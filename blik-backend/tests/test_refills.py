import logging
from datetime import date, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Customer, RefillRequest

VALID = {
    "prescription_number": "RX-2024-0042",
    "date_of_birth": "1985-03-21",
    "phone": "0903 123 4567",
    "method": "pickup",
}


def payload(**overrides):
    return {**VALID, **overrides}


def count(engine, model):
    with Session(engine) as db:
        return db.scalar(select(func.count()).select_from(model))


def test_saves_request_and_customer(client, db_engine):
    response = client.post("/refills", json=VALID)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "new"
    assert body["method"] == "pickup"
    assert body["id"] >= 1
    # The public confirmation must not echo personal data.
    assert "+234" not in response.text
    assert "RX-2024" not in response.text

    with Session(db_engine) as db:
        customer = db.scalars(select(Customer)).one()
        refill = db.scalars(select(RefillRequest)).one()
        assert customer.phone == "+2349031234567"
        assert str(customer.date_of_birth) == "1985-03-21"
        assert refill.customer_id == customer.id
        assert refill.prescription_number == "RX-2024-0042"
        assert refill.status.value == "new"


@pytest.mark.parametrize(
    "phone",
    [
        "09031234567",
        "0903 123 4567",
        "0903-123-4567",
        "+2349031234567",
        "+234 903 123 4567",
        "2349031234567",
        "+234 (0) 903 123 4567",
    ],
)
def test_phone_formats_are_stored_as_plus_234(client, db_engine, phone):
    assert client.post("/refills", json=payload(phone=phone)).status_code == 201
    with Session(db_engine) as db:
        assert db.scalars(select(Customer)).one().phone == "+2349031234567"


@pytest.mark.parametrize("phone", ["", "12345", "0803", "+12025550100", "06031234567", "abc"])
def test_invalid_phone_rejected(client, db_engine, phone):
    response = client.post("/refills", json=payload(phone=phone))
    assert response.status_code == 422
    assert count(db_engine, RefillRequest) == 0


@pytest.mark.parametrize(
    "overrides",
    [
        {"method": "courier"},
        {"date_of_birth": (date.today() + timedelta(days=1)).isoformat()},
        {"date_of_birth": "not-a-date"},
        {"prescription_number": "x"},
        {"prescription_number": "RX 123; DROP TABLE"},
    ],
)
def test_invalid_fields_rejected(client, db_engine, overrides):
    assert client.post("/refills", json=payload(**overrides)).status_code == 422
    assert count(db_engine, RefillRequest) == 0


def test_missing_field_rejected(client):
    body = payload()
    del body["prescription_number"]
    assert client.post("/refills", json=body).status_code == 422


def test_validation_errors_do_not_echo_input(client):
    response = client.post("/refills", json=payload(phone="my-secret-input-123"))
    assert response.status_code == 422
    assert "my-secret-input-123" not in response.text


def test_same_phone_and_dob_reuses_customer(client, db_engine):
    client.post("/refills", json=VALID)
    client.post("/refills", json=payload(phone="+234 903 123 4567", prescription_number="RX-2"))

    assert count(db_engine, Customer) == 1
    assert count(db_engine, RefillRequest) == 2


def test_same_phone_different_dob_is_a_different_customer(client, db_engine):
    client.post("/refills", json=VALID)
    client.post("/refills", json=payload(date_of_birth="2012-07-01"))

    assert count(db_engine, Customer) == 2


def test_rate_limited_per_ip(client, monkeypatch):
    monkeypatch.setattr(settings, "refill_rate_limit_per_minute", 2)

    assert client.post("/refills", json=VALID).status_code == 201
    assert client.post("/refills", json=VALID).status_code == 201
    blocked = client.post("/refills", json=VALID)

    assert blocked.status_code == 429
    assert "retry-after" in blocked.headers


def test_phone_and_prescription_numbers_are_not_logged(client, caplog):
    caplog.set_level(logging.DEBUG)

    client.post("/refills", json=VALID)
    client.post("/refills", json=payload(phone="09031234568", date_of_birth="not-a-date"))

    for secret in ("9031234567", "9031234568", "RX-2024-0042"):
        assert secret not in caplog.text


def test_cors_allows_only_the_configured_origin(client):
    preflight = {"Access-Control-Request-Method": "POST"}

    allowed = client.options("/refills", headers={"Origin": "https://blik.example", **preflight})
    assert allowed.headers.get("access-control-allow-origin") == "https://blik.example"

    other = client.options("/refills", headers={"Origin": "https://evil.example", **preflight})
    assert "access-control-allow-origin" not in other.headers
