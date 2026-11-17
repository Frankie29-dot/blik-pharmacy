from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.deps import DbSession, get_current_staff
from app.models import Customer, RefillRequest, RefillStatus
from app.ratelimit import refill_limiter
from app.schemas import RefillConfirmation, RefillCreate, RefillOut, RefillStatusUpdate

router = APIRouter(prefix="/refills", tags=["refills"])


def get_or_create_customer(db: Session, phone: str, date_of_birth: date) -> Customer:
    lookup = select(Customer).where(
        Customer.phone == phone, Customer.date_of_birth == date_of_birth
    )
    customer = db.scalar(lookup)
    if customer is not None:
        return customer

    customer = Customer(phone=phone, date_of_birth=date_of_birth)
    db.add(customer)
    try:
        db.flush()
    except IntegrityError:
        # Two identical submissions raced; the other one won. Use its row.
        db.rollback()
        customer = db.scalar(lookup)
        if customer is None:
            raise
    return customer


@router.post(
    "",
    response_model=RefillConfirmation,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(refill_limiter)],
)
def create_refill(payload: RefillCreate, db: DbSession) -> RefillConfirmation:
    """Public endpoint used by the website's refill form."""
    customer = get_or_create_customer(db, payload.phone, payload.date_of_birth)
    refill = RefillRequest(
        customer_id=customer.id,
        prescription_number=payload.prescription_number,
        method=payload.method,
        status=RefillStatus.new,
    )
    db.add(refill)
    db.commit()
    db.refresh(refill)

    return RefillConfirmation(
        id=refill.id,
        status=refill.status,
        method=refill.method,
        created_at=refill.created_at,
        message=f"Thank you. Your refill request (reference #{refill.id}) has been received.",
    )


@router.get("", response_model=list[RefillOut], dependencies=[Depends(get_current_staff)])
def list_refills(
    db: DbSession,
    status_filter: Annotated[RefillStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """Staff only. Newest first; optionally filter with ?status=new."""
    query = select(RefillRequest).order_by(RefillRequest.created_at.desc(), RefillRequest.id.desc())
    if status_filter is not None:
        query = query.where(RefillRequest.status == status_filter)
    return db.scalars(query.limit(limit).offset(offset)).all()


@router.patch("/{refill_id}", response_model=RefillOut, dependencies=[Depends(get_current_staff)])
def update_refill(refill_id: int, payload: RefillStatusUpdate, db: DbSession):
    """Staff only. Change a request's status."""
    refill = db.get(RefillRequest, refill_id)
    if refill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Refill request not found")
    refill.status = payload.status
    db.commit()
    db.refresh(refill)
    return refill
