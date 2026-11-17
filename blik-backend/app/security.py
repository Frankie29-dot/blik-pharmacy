from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.config import settings
from app.models import Staff

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


# Verified against when the email is unknown, so "no such user" takes about as long
# as "wrong password" and login can't be used to discover which emails exist.
DUMMY_HASH = hash_password("not-a-real-password")


def create_access_token(staff: Staff) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(staff.id),
        "role": staff.role.value,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    """Return the token's claims, or None if it is invalid or expired."""
    try:
        return jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError:
        return None
