import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import User

SECRET = os.getenv("SECRET_KEY", "dev-only-change-me")
ALGO = "HS256"
TOKEN_TTL_MIN = int(os.getenv("TOKEN_TTL_MIN", "60"))
ITERATIONS = 200_000
bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), ITERATIONS).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    salt, digest = stored.split("$", 1)
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), ITERATIONS).hex()
    return hmac.compare_digest(candidate, digest)


def create_token(user_id: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_TTL_MIN)
    return jwt.encode({"sub": str(user_id), "exp": exp}, SECRET, algorithm=ALGO)


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(401, "Missing bearer token")
    try:
        payload = jwt.decode(creds.credentials, SECRET, algorithms=[ALGO])
        user = db.get(User, int(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(401, "Invalid or expired token")
    if user is None:
        raise HTTPException(401, "User no longer exists")
    return user
