from __future__ import annotations

from app.grader.base import BaseTaskGrader, TaskGradeResult
from app.models import DeductionItem


class BasicTasksGrader(BaseTaskGrader):
    """문제1: 기본작업 (총 20점) 채점기 뼈대.

    - 기본작업-1 (데이터 입력): 5점 (부분점수 없음, 하나라도 틀리면 0점)
    - 기본작업-2 (셀 서식/조건부 서식 등): 10점 (총 5문제, 각 2점씩 부분점수 있음)
    - 기본작업-3 (고급필터, 조건부서식 등): 5점 (부분점수 없음)
    """

    MAX_SCORE = 20

    def grade(self) -> TaskGradeResult:
        deductions: list[DeductionItem] = []
        score = 0

        score += self._grade_basic_1(deductions)
        score += self._grade_basic_2(deductions)
        score += self._grade_basic_3(deductions)

        return TaskGradeResult(score=score, max_score=self.MAX_SCORE, deductions=deductions)

    def _grade_basic_1(self, deductions: list[DeductionItem]) -> int:
        sheet_name = "기본작업-1"
        if not self.has_sheet(sheet_name):
            deductions.append(
                DeductionItem(
                    problem_no="문제1-1",
                    task_name="기본작업-1 (데이터 입력)",
                    deduction=-5,
                    detail=f"'{sheet_name}' 시트를 찾을 수 없습니다.",
                )
            )
            return 0

        ws = self.wb_values[sheet_name]
        expected_cells: dict[str, str] = self.answer_spec.get("basic_1", {}).get("cells", {})

        # TODO: 실제 회차 정답 셀 좌표와 값을 answer_spec에서 읽어 비교합니다.
        if expected_cells:
            for coord, expected in expected_cells.items():
                actual = self.normalize(ws[coord].value)
                if actual != self.normalize(expected):
                    deductions.append(
                        DeductionItem(
                            problem_no="문제1-1",
                            task_name="기본작업-1 (데이터 입력)",
                            deduction=-5,
                            detail=f"{coord} 셀 값 불일치 (기대: '{expected}', 실제: '{actual}') — 부분점수 없음",
                        )
                    )
                    return 0
            return 5

        # 뼈대 기본 동작: 시트 내 입력된 데이터가 존재하면 통과 예시로 처리
        has_data = ws.max_row > 1 or ws["A1"].value is not None
        if not has_data:
            deductions.append(
                DeductionItem(
                    problem_no="문제1-1",
                    task_name="기본작업-1 (데이터 입력)",
                    deduction=-5,
                    detail="데이터 입력 내용이 비어 있습니다. (하나라도 틀리면 0점)",
                )
            )
            return 0
        return 5

    def _grade_basic_2(self, deductions: list[DeductionItem]) -> int:
        sheet_name = "기본작업-2"
        if not self.has_sheet(sheet_name):
            deductions.append(
                DeductionItem(
                    problem_no="문제1-2",
                    task_name="기본작업-2 (셀 서식)",
                    deduction=-10,
                    detail=f"'{sheet_name}' 시트를 찾을 수 없습니다.",
                )
            )
            return 0

        # 총 5문항, 각 2점 (부분점수 있음)
        sub_tasks = self.answer_spec.get("basic_2", {}).get("sub_tasks", [])
        if not sub_tasks:
            # TODO: 병합/글꼴/표시형식/테두리/이름정의 등 5개 세부 문항 채점 로직 연결
            return 10

        earned = 0
        ws = self.wb_formula[sheet_name]
        for idx, task in enumerate(sub_tasks, start=1):
            cell_ref = task.get("cell", "A1")
            expected_fmt = task.get("number_format")
            if expected_fmt and ws[cell_ref].number_format != expected_fmt:
                deductions.append(
                    DeductionItem(
                        problem_no=f"문제1-2({idx})",
                        task_name=task.get("title", f"기본작업-2 {idx}번"),
                        deduction=-2,
                        detail=f"{cell_ref} 셀 표시형식 불일치",
                    )
                )
            else:
                earned += 2
        return earned

    def _grade_basic_3(self, deductions: list[DeductionItem]) -> int:
        sheet_name = "기본작업-3"
        if not self.has_sheet(sheet_name):
            deductions.append(
                DeductionItem(
                    problem_no="문제1-3",
                    task_name="기본작업-3 (고급필터/조건부서식)",
                    deduction=-5,
                    detail=f"'{sheet_name}' 시트를 찾을 수 없습니다.",
                )
            )
            return 0

        # TODO: 고급필터 결과 영역 또는 조건부서식 규칙(conditional_formatting) 검증 구현
        ws = self.wb_formula[sheet_name]
        has_cf = len(ws.conditional_formatting) > 0
        if not has_cf and self.answer_spec.get("basic_3", {}).get("require_cf", False):
            deductions.append(
                DeductionItem(
                    problem_no="문제1-3",
                    task_name="기본작업-3 (고급필터/조건부서식)",
                    deduction=-5,
                    detail="조건부 서식이 적용되지 않았습니다. (부분점수 없음)",
                )
            )
            return 0
        return 5
