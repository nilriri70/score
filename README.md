# 컴퓨터활용능력 2급 실기 자동채점 프로그램 (뼈대)

레퍼런스 UI, 점수별 통계 보기, 채점 기준(총 100점 / 70점 이상 합격) 및 샘플 `.xlsm` 시트 구성을 기반으로 구성한 FastAPI + SQLite + Chart.js 기반 자동채점 프로그램 뼈대입니다.

## 프로젝트 구조

- `app/main.py` — FastAPI 웹 서버 및 API 엔드포인트 (`/`, `/statistics`, `/api/rounds`, `/api/grade`, `/api/overview`, `/api/statistics`)
- `app/database.py` — SQLite(`data/submissions.db`) 초기화, 채점 기록 저장, 누적점수 순위 및 점수 구간별 분포 집계
- `app/models.py` — 채점 결과 및 감점 내역 Pydantic 스키마
- `app/grader/` — 영역별 채점기 뼈대
  - `basic_tasks.py`: 문제1 기본작업 (총 20점: 기본작업-1 `5점`, 기본작업-2 `10점/부분점수`, 기본작업-3 `5점`)
  - `calc_tasks.py`: 문제2 계산작업 (총 40점: 함수 5문제×`8점`, 결과값 기준 채점)
  - `analysis_tasks.py`: 문제3 분석작업 (총 20점: 분석작업-1/2 각 `10점`, 부분점수 없음)
  - `etc_tasks.py`: 문제4 기타작업 (총 20점: 매크로 2문제×`5점` 부분점수, 차트 5문항×`2점` 부분점수)
  - `engine.py`: 통합 채점 오케스트레이터
- `data/problems/` — 회차별 문제 `.xlsm` 파일 및 정답 기준(`rounds.json`)
- `static/` — 프론트엔드 UI (`index.html`, `statistics.html`, `css/styles.css`, `js/app.js`, `js/statistics.js`)

## 실행 방법

```powershell
uv run uvicorn app.main:app --reload
```

실행 후 브라우저에서 `http://127.0.0.1:8000` 으로 접속하세요.
