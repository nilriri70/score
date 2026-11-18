from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any

import openpyxl

from app.grader.analysis_tasks import AnalysisTasksGrader
from app.grader.basic_tasks import BasicTasksGrader
from app.grader.calc_tasks import CalcTasksGrader
from app.grader.etc_tasks import EtcTasksGrader
from app.models import DeductionItem, GradingResponse, SectionScore

PASSING_SCORE = 70


def grade_workbook(
    file_bytes: bytes,
    filename: str,
    round_info: dict[str, Any],
    teacher_id: str,
    student_nickname: str,
) -> GradingResponse:
    """업로드된 엑셀(.xlsm/.xlsx) 파일을 채점하여 영역별 점수 및 감점 내역을 반환합니다."""
    is_macro_enabled = filename.lower().endswith(".xlsm")

    wb_formula = openpyxl.load_workbook(
        BytesIO(file_bytes), data_only=False, keep_vba=is_macro_enabled
    )
    wb_values = openpyxl.load_workbook(
        BytesIO(file_bytes), data_only=True, keep_vba=False
    )

    answer_spec: dict[str, Any] = round_info.get("answer_spec", {})

    r1 = BasicTasksGrader(wb_formula, wb_values, answer_spec).grade()
    r2 = CalcTasksGrader(wb_formula, wb_values, answer_spec).grade()
    r3 = AnalysisTasksGrader(wb_formula, wb_values, answer_spec).grade()
    r4 = EtcTasksGrader(wb_formula, wb_values, answer_spec).grade()

    deductions: list[DeductionItem] = [
        *r1.deductions,
        *r2.deductions,
        *r3.deductions,
        *r4.deductions,
    ]

    total = r1.score + r2.score + r3.score + r4.score

    return GradingResponse(
        round_id=round_info["id"],
        round_name=round_info["name"],
        teacher_id=teacher_id or "미입력",
        student_nickname=student_nickname or "익명학생",
        filename=filename,
        scores=SectionScore(
            problem1=r1.score,
            problem2=r2.score,
            problem3=r3.score,
            problem4=r4.score,
        ),
        total_score=total,
        passed=total >= PASSING_SCORE,
        deductions=deductions,
        graded_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
