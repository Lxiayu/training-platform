"""密码哈希与令牌签发（仅标准库，零额外依赖）。

- 密码：PBKDF2-SHA256（10 万轮），落盘格式 ``pbkdf2$<salt>$<hex>``
- 令牌：HMAC-SHA256 签名的轻量 token，格式 ``base64url(payload).sig``

仅用于原型演示；正式版可无缝替换为 PyJWT（接口形状不变）。
"""
import base64
import hashlib
import hmac
import json
import secrets
import time

from app.core.config import TOKEN_SECRET, TOKEN_TTL_SECONDS

_ITERATIONS = 100_000


# ---------- 密码 ----------

def hash_password(password: str, *, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), _ITERATIONS
    )
    return f"pbkdf2${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, _ = (stored or "").split("$", 2)
    except ValueError:
        return False
    return hmac.compare_digest(hash_password(password, salt=salt), stored)


# ---------- 令牌 ----------

def _sign(body: str) -> str:
    return hmac.new(
        TOKEN_SECRET.encode("utf-8"), body.encode("ascii"), hashlib.sha256
    ).hexdigest()


def create_token(username: str, *, ttl: int = TOKEN_TTL_SECONDS) -> str:
    payload = json.dumps(
        {"u": username, "exp": int(time.time()) + ttl},
        separators=(",", ":"), ensure_ascii=False,
    )
    body = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")
    return f"{body}.{_sign(body)}"


def parse_token(token: str) -> str | None:
    """校验签名与有效期；通过返回用户名，否则返回 None。"""
    try:
        body, sig = token.split(".", 1)
        if not hmac.compare_digest(_sign(body), sig):
            return None
        payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if not isinstance(payload, dict) or payload.get("exp", 0) < time.time():
            return None
        return payload.get("u")
    except Exception:
        return None
