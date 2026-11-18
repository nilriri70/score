from __future__ import annotations

from pydantic import BaseModel, Field


class DeductionItem(BaseModel):
    """감점 내역 한 건을 나타내는 모델."""

    problem_no: str = Field(..., description="문제번호 (예: 문제1-1, 문제2-3)")
    task_name: str = Field(..., description="작업내용 (예: 기본작업-1, 계산작업 1번)")
    deduction: int = Field(..., description="감점 점수 (예: -5, -8)")
    detail: str = Field(..., description="오류 상세내용")


class SectionScore(BaseModel):
    """영역별 상세 점수."""

    problem1: int = Field(0, ge=0, le=20, description="문제1 기본작업 (20점 만점)")
    problem2: int = Field(0, ge=0, le=40, description="문제2 계산작업 (40점 만점)")
    problem3: int = Field(0, ge=0, le=20, description="문제3 분석작업 (20점 만점)")
    problem4: int = Field(0, ge=0, le=20, description="문제4 기타작업 (20점 만점)")


class GradingResponse(BaseModel):
    """자동채점 API 응답 모델."""

    round_id: str
    round_name: str
    teacher_id: str
    student_nickname: str
    filename: str
    scores: SectionScore
    total_score: int = Field(..., ge=0, le=100)
    passed: bool
    deductions: list[DeductionItem]
    graded_at: str
