from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from openpyxl.workbook import Workbook

from app.models import DeductionItem


@dataclass
class TaskGradeResult:
    """단일 영역(문제1~4) 채점 결과."""

    score: int
    max_score: int
    deductions: list[DeductionItem] = field(default_factory=list)


class BaseTaskGrader:
    """모든 영역별 채점기의 공통 베이스 클래스."""

    def __init__(self, wb_formula: Workbook, wb_values: Workbook, answer_spec: dict[str, Any]) -> None:
        self.wb_formula = wb_formula
        self.wb_values = wb_values
        self.answer_spec = answer_spec

    def has_sheet(self, sheet_name: str) -> bool:
        return sheet_name in self.wb_formula.sheetnames

    @staticmethod
    def normalize(value: Any) -> str:
        """비교를 위해 셀 값을 문자열로 정규화합니다."""
        if value is None:
            return ""
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value).strip()
