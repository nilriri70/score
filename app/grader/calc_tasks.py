from __future__ import annotations

from app.grader.base import BaseTaskGrader, TaskGradeResult
from app.models import DeductionItem


class CalcTasksGrader(BaseTaskGrader):
    """문제2: 계산작업 (총 40점) 채점기 뼈대.

    - 함수 문제: 총 5문제 (각 8점씩, 부분점수 없음)
    - 결과값이 정답과 일치하면 함수식의 세부 구조나 셀 참조 방식($ 사용 여부 등)이 달라도 정답 인정
    """

    MAX_SCORE = 40
    POINTS_PER_QUESTION = 8

    def grade(self) -> TaskGradeResult:
        deductions: list[DeductionItem] = []
        sheet_name = "계산작업"

        if not self.has_sheet(sheet_name):
            deductions.append(
                DeductionItem(
                    problem_no="문제2",
                    task_name="계산작업",
                    deduction=-self.MAX_SCORE,
                    detail=f"'{sheet_name}' 시트를 찾을 수 없습니다.",
                )
            )
            return TaskGradeResult(score=0, max_score=self.MAX_SCORE, deductions=deductions)

        ws_formula = self.wb_formula[sheet_name]
        ws_values = self.wb_values[sheet_name]
        questions = self.answer_spec.get("calc", [])

        if not questions:
            # 뼈대 기본 동작: 5개 문항의 샘플 수식 작성 여부 점검
            # TODO: data/problems/rounds.json 에 회차별 5개 함수 문제 셀 범위/정답값을 정의하세요.
            deductions.append(
                DeductionItem(
                    problem_no="문제2-1~5",
                    task_name="계산작업 (함수 5문항)",
                    deduction=-self.MAX_SCORE,
                    detail="회차 정답 기준이 미등록 상태이거나 수식이 입력되지 않았습니다. (채점 기준 연동 필요)",
                )
            )
            return TaskGradeResult(score=0, max_score=self.MAX_SCORE, deductions=deductions)

        score = 0
        for idx, q in enumerate(questions[:5], start=1):
            target_cells: list[str] = q.get("cells", [])
            expected_values: list[str] = q.get("expected_values", [])
            all_correct = True
            fail_reason = ""

            for cell_ref, exp_val in zip(target_cells, expected_values):
                raw_formula = ws_formula[cell_ref].value
                cached_val = self.normalize(ws_values[cell_ref].value)

                if not isinstance(raw_formula, str) or not raw_formula.startswith("="):
                    all_correct = False
                    fail_reason = f"{cell_ref} 셀에 수식(=)이 입력되지 않았습니다."
                    break

                if cached_val != self.normalize(exp_val):
                    all_correct = False
                    fail_reason = f"{cell_ref} 결과값 불일치 (기대: '{exp_val}', 실제: '{cached_val}')"
                    break

            if all_correct and target_cells:
                score += self.POINTS_PER_QUESTION
            else:
                deductions.append(
                    DeductionItem(
                        problem_no=f"문제2-{idx}",
                        task_name=q.get("title", f"계산작업 {idx}번"),
                        deduction=-self.POINTS_PER_QUESTION,
                        detail=fail_reason or "정답 범위 검증 실패 (부분점수 없음)",
                    )
                )

        return TaskGradeResult(score=score, max_score=self.MAX_SCORE, deductions=deductions)
