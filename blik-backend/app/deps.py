from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Staff
from app.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

DbSession = Annotated[Session, Depends(get_db)]


def get_current_staff(token: Annotated[str, Depends(oauth2_scheme)], db: DbSession) -> Staff:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    claims = decode_access_token(token)
    if claims is None:
        raise unauthorized
    try:
        staff_id = int(claims["sub"])
    except (KeyError, ValueError):
        raise unauthorized from None

    # Look the account up on every request, so a deleted account stops working at once.
    staff = db.get(Staff, staff_id)
    if staff is None:
        raise unauthorized
    return staff
