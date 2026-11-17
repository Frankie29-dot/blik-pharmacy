from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import RefillMethod, RefillStatus
from app.phone import normalize_ng_phone


class RefillCreate(BaseModel):
    """Body of the public refill form."""

    model_config = ConfigDict(str_strip_whitespace=True)

    prescription_number: str = Field(
        min_length=3, max_length=40, pattern=r"^[A-Za-z0-9][A-Za-z0-9/-]*$"
    )
    date_of_birth: date
    phone: str = Field(min_length=1, max_length=32)
    method: RefillMethod

    @field_validator("prescription_number")
    @classmethod
    def _uppercase_prescription(cls, value: str) -> str:
        return value.upper()

    @field_validator("phone")
    @classmethod
    def _normalize_phone(cls, value: str) -> str:
        return normalize_ng_phone(value)

    @field_validator("date_of_birth")
    @classmethod
    def _plausible_dob(cls, value: date) -> date:
        if value >= date.today():
            raise ValueError("Date of birth must be in the past")
        if value.year < 1900:
            raise ValueError("Date of birth is not valid")
        return value


class RefillConfirmation(BaseModel):
    """What the public gets back. Deliberately contains no personal data."""

    id: int
    status: RefillStatus
    method: RefillMethod
    created_at: datetime
    message: str


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str | None
    phone: str
    date_of_birth: date


class RefillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    prescription_number: str
    method: RefillMethod
    status: RefillStatus
    created_at: datetime
    updated_at: datetime
    customer: CustomerOut


class RefillStatusUpdate(BaseModel):
    status: RefillStatus


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
