from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any


def _resolve_db_path() -> Path:
    """Vercel 등 읽기 전용 환경에서는 /tmp 경로를 사용합니다."""
    if os.environ.get("VERCEL"):
        return Path("/tmp/submissions.db")
    local_path = Path(__file__).resolve().parent.parent / "data" / "submissions.db"
    try:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        test_file = local_path.parent / ".write_test"
        test_file.touch()
        test_file.unlink()
        return local_path
    except OSError:
        return Path("/tmp/submissions.db")


DB_PATH = _resolve_db_path()


_INITIALIZED = False


def get_connection() -> sqlite3.Connection:
    """SQLite 데이터베이스 연결을 반환합니다."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """테이블을 생성하고 초기 데모 데이터를 시드합니다."""
    global _INITIALIZED
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                round_id TEXT NOT NULL,
                teacher_id TEXT NOT NULL,
                student_nickname TEXT NOT NULL,
                filename TEXT NOT NULL,
                score_p1 INTEGER NOT NULL,
                score_p2 INTEGER NOT NULL,
                score_p3 INTEGER NOT NULL,
                score_p4 INTEGER NOT NULL,
                total_score INTEGER NOT NULL,
                passed INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
            """
        )

        count = conn.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]
        if count == 0:
            _seed_demo_data(conn)
    _INITIALIZED = True


def _ensure_initialized() -> None:
    if not _INITIALIZED:
        init_db()


def _seed_demo_data(conn: sqlite3.Connection) -> None:
    """통계/순위 화면 확인을 위한 초기 샘플 데이터를 삽입합니다."""
    sample_rows = [
        ("sample_01", "t_kim01", "오*진", "sample.xlsm", 20, 32, 20, 18, 90, 1),
        ("sample_01", "t_kim01", "봉*수", "sample.xlsm", 18, 40, 10, 16, 84, 1),
        ("sample_01", "t_park2", "송*라", "sample.xlsm", 15, 24, 20, 15, 74, 1),
        ("sample_01", "t_park2", "김*민", "sample.xlsm", 10, 16, 10, 10, 46, 0),
        ("sample_01", "t_lee03", "이*현", "sample.xlsm", 20, 40, 20, 20, 100, 1),
        ("sample_01", "t_lee03", "박*우", "sample.xlsm", 5, 8, 0, 4, 17, 0),
        ("sample_01", "t_choi4", "정*서", "sample.xlsm", 12, 16, 10, 12, 50, 0),
        ("sample_01", "t_kim01", "최*아", "sample.xlsm", 0, 0, 0, 5, 5, 0),
        ("sample_01", "t_park2", "강*준", "sample.xlsm", 2, 0, 0, 2, 4, 0),
        ("sample_01", "t_jung5", "윤*호", "sample.xlsm", 15, 24, 10, 14, 63, 0),
    ]
    conn.executemany(
        """
        INSERT INTO submissions (
            round_id, teacher_id, student_nickname, filename,
            score_p1, score_p2, score_p3, score_p4, total_score, passed
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        sample_rows,
    )


def save_submission(
    round_id: str,
    teacher_id: str,
    student_nickname: str,
    filename: str,
    p1: int,
    p2: int,
    p3: int,
    p4: int,
    total: int,
    passed: bool,
) -> None:
    """채점 결과를 DB에 저장합니다."""
    _ensure_initialized()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO submissions (
                round_id, teacher_id, student_nickname, filename,
                score_p1, score_p2, score_p3, score_p4, total_score, passed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                round_id,
                teacher_id or "미입력",
                student_nickname or "익명학생",
                filename,
                p1,
                p2,
                p3,
                p4,
                total,
                1 if passed else 0,
            ),
        )


def get_overview_stats(round_id: str | None = None) -> dict[str, Any]:
    """인원수, 평균점수 및 학생/선생님 누적점수 순위를 반환합니다."""
    _ensure_initialized()
    with get_connection() as conn:
        where = "WHERE round_id = ?" if round_id else ""
        params = (round_id,) if round_id else ()

        summary = conn.execute(
            f"SELECT COUNT(*) AS cnt, COALESCE(AVG(total_score), 0) AS avg_score FROM submissions {where}",
            params,
        ).fetchone()

        student_ranks = conn.execute(
            """
            SELECT student_nickname AS name, SUM(total_score) AS total
            FROM submissions
            WHERE student_nickname != '익명학생'
            GROUP BY student_nickname
            ORDER BY total DESC
            LIMIT 10
            """
        ).fetchall()

        teacher_ranks = conn.execute(
            """
            SELECT teacher_id AS name, SUM(total_score) AS total
            FROM submissions
            WHERE teacher_id != '미입력'
            GROUP BY teacher_id
            ORDER BY total DESC
            LIMIT 5
            """
        ).fetchall()

    return {
        "participant_count": summary["cnt"],
        "average_score": round(float(summary["avg_score"]), 2),
        "student_rankings": [dict(r) for r in student_ranks],
        "teacher_rankings": [dict(r) for r in teacher_ranks],
    }


def _bucket_distribution(values: list[int], bins: list[tuple[str, int, int, bool]]) -> list[dict[str, Any]]:
    """점수 리스트를 구간별로 집계합니다. (label, low, high, inclusive_high)"""
    result = []
    for label, low, high, inc_high in bins:
        if inc_high:
            cnt = sum(1 for v in values if low <= v <= high)
        else:
            cnt = sum(1 for v in values if low <= v < high)
        result.append({"label": label, "count": cnt, "low": low, "high": high, "inc_high": inc_high})
    return result


def get_round_statistics(round_id: str) -> dict[str, Any]:
    """특정 회차의 총점 및 문제1~4 구간별 분포 통계를 반환합니다."""
    _ensure_initialized()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT total_score, score_p1, score_p2, score_p3, score_p4 FROM submissions WHERE round_id = ?",
            (round_id,),
        ).fetchall()

    totals = [r["total_score"] for r in rows]
    p1s = [r["score_p1"] for r in rows]
    p2s = [r["score_p2"] for r in rows]
    p3s = [r["score_p3"] for r in rows]
    p4s = [r["score_p4"] for r in rows]

    total_bins = [(f"{i}~{i + 10}점미만", i, i + 10, False) for i in range(0, 100, 10)] + [
        ("100", 100, 100, True)
    ]
    bins_20 = [
        ("0~5점미만", 0, 5, False),
        ("5~10점미만", 5, 10, False),
        ("10~15점미만", 10, 15, False),
        ("15~20점미만", 15, 20, False),
        ("20", 20, 20, True),
    ]
    bins_40 = [(f"{i}~{i + 5}점미만", i, i + 5, False) for i in range(0, 40, 5)] + [("40", 40, 40, True)]

    return {
        "round_id": round_id,
        "count": len(rows),
        "total": _bucket_distribution(totals, total_bins),
        "problem1": _bucket_distribution(p1s, bins_20),
        "problem2": _bucket_distribution(p2s, bins_40),
        "problem3": _bucket_distribution(p3s, bins_20),
        "problem4": _bucket_distribution(p4s, bins_20),
    }
