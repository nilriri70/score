from __future__ import annotations

import json
import zipfile
from contextlib import asynccontextmanager
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.database import get_overview_stats, get_round_statistics, init_db, save_submission
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


@app.get("/")
async def index_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


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
) -> GradingResponse:
    filename = file.filename or "uploaded.xlsm"
    if not filename.lower().endswith((".xlsm", ".xlsx")):
        raise HTTPException(status_code=400, detail=".xlsm 또는 .xlsx 파일만 채점할 수 있습니다.")

    round_info = get_round_by_id(round_id)
    file_bytes = await file.read()

    try:
        result = grade_workbook(
            file_bytes=file_bytes,
            filename=filename,
            round_info=round_info,
            teacher_id=teacher_id.strip(),
            student_nickname=student_nickname.strip(),
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
