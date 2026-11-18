from __future__ import annotations

import json
import zipfile
from contextlib import asynccontextmanager
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi import Cookie, Depends, FastAPI, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.auth import SESSION_COOKIE_NAME, create_session_token, parse_session_token, verify_password
from app.database import (
    create_user,
    get_overview_stats,
    get_round_statistics,
    get_user_by_username,
    init_db,
    save_submission,
)
from app.grader import grade_workbook
from app.models import GradingResponse

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PROBLEMS_DIR = DATA_DIR / "problems"
STATIC_DIR = BASE_DIR / "static"


def load_rounds() -> list[dict[str, Any]]:
    rounds_file = PROBLEMS_DIR / "rounds.json"
    if not rounds_file.exists():
        return []
    return json.loads(rounds_file.read_text(encoding="utf-8"))


def get_round_by_id(round_id: str) -> dict[str, Any]:
    for item in load_rounds():
        if item["id"] == round_id:
            return item
    raise HTTPException(status_code=404, detail="선택한 회차를 찾을 수 없습니다.")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="컴퓨터활용능력 2급 실기 자동채점 프로그램",
    version="0.1.0",
    lifespan=lifespan,
)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=30)
    password: str = Field(..., min_length=4, max_length=100)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=30)
    password: str = Field(..., min_length=4, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=30)
    role: str = Field(default="student", pattern="^(student|teacher)$")


def get_optional_user(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> dict[str, Any] | None:
    return parse_session_token(session_token)


def require_current_user(
    user: dict[str, Any] | None = Depends(get_optional_user),
) -> dict[str, Any]:
    if user is None:
        raise HTTPException(status_code=401, detail="채점을 진행하려면 먼저 로그인해야 합니다.")
    return user


@app.get("/")
async def index_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/auth/me")
async def auth_me(user: dict[str, Any] | None = Depends(get_optional_user)) -> dict[str, Any]:
    return {"authenticated": user is not None, "user": user}


@app.post("/api/auth/login")
async def auth_login(body: LoginRequest, response: Response) -> dict[str, Any]:
    user = get_user_by_username(body.username.strip())
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")

    token = create_session_token(user)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )
    return {
        "authenticated": True,
        "user": {
            "username": user["username"],
            "display_name": user["display_name"],
            "role": user["role"],
        },
    }


@app.post("/api/auth/register")
async def auth_register(body: RegisterRequest, response: Response) -> dict[str, Any]:
    username = body.username.strip()
    if get_user_by_username(username):
        raise HTTPException(status_code=409, detail="이미 사용 중인 아이디입니다.")

    user = create_user(
        username=username,
        password=body.password,
        display_name=body.display_name.strip(),
        role=body.role,
    )
    token = create_session_token(user)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )
    return {"authenticated": True, "user": user}


@app.post("/api/auth/logout")
async def auth_logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(key=SESSION_COOKIE_NAME)
    return {"ok": True}


@app.get("/statistics")
async def statistics_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "statistics.html")


@app.get("/api/rounds")
async def list_rounds() -> list[dict[str, str]]:
    return [
        {"id": r["id"], "name": r["name"], "description": r.get("description", "")}
        for r in load_rounds()
    ]


@app.get("/api/rounds/{round_id}/download")
async def download_round_file(round_id: str) -> FileResponse:
    round_info = get_round_by_id(round_id)
    file_path = PROBLEMS_DIR / round_info["file"]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="문제 파일이 존재하지 않습니다.")
    return FileResponse(
        path=file_path,
        filename=f"{round_info['name']}_{round_info['file']}",
        media_type="application/vnd.ms-excel.sheet.macroEnabled.12",
    )


@app.get("/api/rounds/download-all")
async def download_all_rounds() -> StreamingResponse:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        added: set[str] = set()
        for r in load_rounds():
            file_path = PROBLEMS_DIR / r["file"]
            if file_path.exists() and file_path.name not in added:
                zf.write(file_path, arcname=file_path.name)
                added.add(file_path.name)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="all_problems.zip"'},
    )


@app.post("/api/grade", response_model=GradingResponse)
async def grade_file(
    round_id: str = Form(...),
    teacher_id: str = Form(""),
    student_nickname: str = Form(""),
    file: UploadFile = File(...),
    current_user: dict[str, Any] = Depends(require_current_user),
) -> GradingResponse:
    filename = file.filename or "uploaded.xlsm"
    if not filename.lower().endswith((".xlsm", ".xlsx")):
        raise HTTPException(status_code=400, detail=".xlsm 또는 .xlsx 파일만 채점할 수 있습니다.")

    round_info = get_round_by_id(round_id)
    file_bytes = await file.read()

    resolved_teacher = teacher_id.strip() or (
        current_user["username"] if current_user.get("role") == "teacher" else ""
    )
    resolved_student = student_nickname.strip() or current_user.get("display_name", "")

    try:
        result = grade_workbook(
            file_bytes=file_bytes,
            filename=filename,
            round_info=round_info,
            teacher_id=resolved_teacher,
            student_nickname=resolved_student,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"엑셀 파일 분석 중 오류가 발생했습니다: {exc}") from exc

    save_submission(
        round_id=result.round_id,
        teacher_id=result.teacher_id,
        student_nickname=result.student_nickname,
        filename=result.filename,
        p1=result.scores.problem1,
        p2=result.scores.problem2,
        p3=result.scores.problem3,
        p4=result.scores.problem4,
        total=result.total_score,
        passed=result.passed,
    )

    return result


@app.get("/api/overview")
async def overview(round_id: str | None = Query(default=None)) -> dict[str, Any]:
    return get_overview_stats(round_id)


@app.get("/api/statistics")
async def statistics(round_id: str = Query(default="sample_01")) -> dict[str, Any]:
    return get_round_statistics(round_id)


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
