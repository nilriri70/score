from __future__ import annotations

from app.grader.base import BaseTaskGrader, TaskGradeResult
from app.models import DeductionItem


class EtcTasksGrader(BaseTaskGrader):
    """문제4: 기타작업 (총 20점) 채점기 뼈대.

    - 매크로 작업: 총 2문제 (각 5점, 총 10점) — 매크로 기록 및 버튼/도형 생성 연결에 부분점수 있음
    - 차트 작업: 총 5문항 (각 2점, 총 10점) — 세부 지시사항별로 부분점수 있음
    """

    MAX_SCORE = 20

    def grade(self) -> TaskGradeResult:
        deductions: list[DeductionItem] = []
        score = 0

        score += self._grade_macro(deductions)
        score += self._grade_chart(deductions)

        return TaskGradeResult(score=score, max_score=self.MAX_SCORE, deductions=deductions)

    def _grade_macro(self, deductions: list[DeductionItem]) -> int:
        sheet_name = "매크로작업"
        if not self.has_sheet(sheet_name):
            deductions.append(
                DeductionItem(
                    problem_no="문제4-1",
                    task_name="매크로작업",
                    deduction=-10,
                    detail=f"'{sheet_name}' 시트를 찾을 수 없습니다.",
                )
            )
            return 0

        # .xlsm VBA 프로젝트 존재 여부 확인 (세부 매크로 파싱은 vbaProject.bin 분석기 연동)
        has_vba = self.wb_formula.vba_archive is not None
        if not has_vba:
            deductions.append(
                DeductionItem(
                    problem_no="문제4-1",
                    task_name="매크로작업 (VBA 매크로)",
                    deduction=-10,
                    detail="매크로(vbaProject.bin)가 포함되어 있지 않습니다. (.xlsm 형식 확인 필요)",
                )
            )
            return 0

        # TODO: oletools 등으로 vbaProject.bin 내 매크로 모듈 및 도형/버튼 연결(onAction) 부분점수 채점 구현
        return 10

    def _grade_chart(self, deductions: list[DeductionItem]) -> int:
        sheet_name = "차트작업"
        if not self.has_sheet(sheet_name):
            deductions.append(
                DeductionItem(
                    problem_no="문제4-2",
                    task_name="차트작업",
                    deduction=-10,
                    detail=f"'{sheet_name}' 시트를 찾을 수 없습니다.",
                )
            )
            return 0

        ws = self.wb_formula[sheet_name]
        charts = getattr(ws, "_charts", [])
        if not charts:
            deductions.append(
                DeductionItem(
                    problem_no="문제4-2",
                    task_name="차트작업 (5문항)",
                    deduction=-10,
                    detail="시트 내 차트 개체를 찾을 수 없습니다.",
                )
            )
            return 0

        chart = charts[0]
        earned = 0

        # 예시 5개 세부 문항(각 2점, 부분점수 있음) 뼈대
        # 1) 차트 제목 존재 여부
        if chart.title is not None:
            earned += 2
        else:
            deductions.append(
                DeductionItem(
                    problem_no="문제4-2(1)",
                    task_name="차트 제목 설정",
                    deduction=-2,
                    detail="차트 제목이 설정되지 않았습니다.",
                )
            )

        # 2) 범례(Legend) 설정 여부
        if chart.legend is not None:
            earned += 2
        else:
            deductions.append(
                DeductionItem(
                    problem_no="문제4-2(2)",
                    task_name="차트 범례 설정",
                    deduction=-2,
                    detail="차트 범례 표시가 누락되었습니다.",
                )
            )

        # 3~5) 데이터 계열/축/레이블 등 세부 지시사항 (TODO: 회차별 정답 스펙 연동)
        earned += 6
        return earned
