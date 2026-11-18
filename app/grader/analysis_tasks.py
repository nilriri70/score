from __future__ import annotations

from app.grader.base import BaseTaskGrader, TaskGradeResult
from app.models import DeductionItem


class AnalysisTasksGrader(BaseTaskGrader):
    """문제3: 분석작업 (총 20점) 채점기 뼈대.

    - 피벗테이블, 시나리오, 목표값 찾기, 부분합, 데이터 표 등
    - 총 2문제 (각 10점씩, 부분점수 없음)
    - 하나라도 조건을 틀리거나 위치가 어긋나면 해당 문제 점수(10점) 전부 감점
    """

    MAX_SCORE = 20
    POINTS_PER_PROBLEM = 10

    def grade(self) -> TaskGradeResult:
        deductions: list[DeductionItem] = []
        score = 0

        for idx, sheet_name in enumerate(["분석작업-1", "분석작업-2"], start=1):
            if not self.has_sheet(sheet_name):
                deductions.append(
                    DeductionItem(
                        problem_no=f"문제3-{idx}",
                        task_name=sheet_name,
                        deduction=-self.POINTS_PER_PROBLEM,
                        detail=f"'{sheet_name}' 시트를 찾을 수 없습니다.",
                    )
                )
                continue

            # TODO: 피벗테이블(ws._pivots), 시나리오/부분합/목표값찾기 결과 셀 검증 로직 구현
            ws_values = self.wb_values[sheet_name]
            spec = self.answer_spec.get(f"analysis_{idx}", {})
            expected_cells: dict[str, str] = spec.get("cells", {})

            if expected_cells:
                mismatch = None
                for coord, exp in expected_cells.items():
                    actual = self.normalize(ws_values[coord].value)
                    if actual != self.normalize(exp):
                        mismatch = f"{coord} 값/위치 불일치 (기대: '{exp}', 실제: '{actual}')"
                        break
                if mismatch:
                    deductions.append(
                        DeductionItem(
                            problem_no=f"문제3-{idx}",
                            task_name=spec.get("title", sheet_name),
                            deduction=-self.POINTS_PER_PROBLEM,
                            detail=f"{mismatch} — 부분점수 없음",
                        )
                    )
                else:
                    score += self.POINTS_PER_PROBLEM
            else:
                # 뼈대 기본 동작: 피벗테이블 존재 여부 또는 시트 데이터 확인
                ws_formula = self.wb_formula[sheet_name]
                has_pivot = bool(getattr(ws_formula, "_pivots", []))
                if has_pivot or ws_values.max_row > 1:
                    score += self.POINTS_PER_PROBLEM
                else:
                    deductions.append(
                        DeductionItem(
                            problem_no=f"문제3-{idx}",
                            task_name=sheet_name,
                            deduction=-self.POINTS_PER_PROBLEM,
                            detail="분석 작업 결과가 확인되지 않았습니다.",
                        )
                    )

        return TaskGradeResult(score=score, max_score=self.MAX_SCORE, deductions=deductions)
