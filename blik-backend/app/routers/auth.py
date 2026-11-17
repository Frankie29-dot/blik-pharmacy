from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.deps import DbSession
from app.models import Staff
from app.ratelimit import login_limiter
from app.schemas import TokenOut
from app.security import DUMMY_HASH, create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut, dependencies=[Depends(login_limiter)])
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession) -> TokenOut:
    """Staff login. Send form fields `username` (the staff email) and `password`."""
    email = form.username.strip().lower()
    staff = db.scalar(select(Staff).where(Staff.email == email))

    password_ok = verify_password(form.password, staff.password_hash if staff else DUMMY_HASH)
    if staff is None or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenOut(access_token=create_access_token(staff))
