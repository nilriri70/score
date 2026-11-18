from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from typing import Any

# Vercel 등 환경변수가 없으면 프로세스용 임시 시크릿 사용
SESSION_SECRET = os.environ.get("SCORE_SESSION_SECRET", "comlicense-score-dev-secret-2026").encode("utf-8")
SESSION_COOKIE_NAME = "score_session"
SESSION_TTL_SECONDS = 60 * 60 * 24 * 7  # 7일


def hash_password(password: str, salt: str | None = None) -> str:
    """PBKDF2-HMAC-SHA256으로 비밀번호를 해시합니다."""
    use_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), use_salt.encode("utf-8"), 100_000)
    return f"{use_salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """저장된 해시와 입력 비밀번호를 상수 시간 비교합니다."""
    try:
        salt, expected_hex = stored_hash.split("$", 1)
    except ValueError:
        return False
    candidate = hash_password(password, salt).split("$", 1)[1]
    return hmac.compare_digest(candidate, expected_hex)


def create_session_token(user: dict[str, Any]) -> str:
    """HMAC-SHA256 서명된 세션 토큰을 생성합니다."""
    payload = {
        "username": user["username"],
        "display_name": user["display_name"],
        "role": user["role"],
        "exp": int(time.time()) + SESSION_TTL_SECONDS,
    }
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    b64 = urlsafe_b64encode(raw).decode("ascii")
    sig = hmac.new(SESSION_SECRET, b64.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{b64}.{sig}"


def parse_session_token(token: str | None) -> dict[str, Any] | None:
    """세션 토큰을 검증하고 사용자 페이로드를 반환합니다."""
    if not token or "." not in token:
        return None
    b64, sig = token.rsplit(".", 1)
    expected_sig = hmac.new(SESSION_SECRET, b64.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected_sig):
        return None
    try:
        payload = json.loads(urlsafe_b64decode(b64.encode("ascii")).decode("utf-8"))
    except Exception:
        return None
    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    return payload
