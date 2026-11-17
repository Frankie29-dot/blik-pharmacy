import os

# Set before the app is imported so the tests never touch a real database or .env secrets.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key-for-pytest-only-" + "x" * 32
os.environ["CORS_ORIGINS"] = "https://blik.example"
os.environ["REFILL_RATE_LIMIT_PER_MINUTE"] = "1000"
os.environ["LOGIN_RATE_LIMIT_PER_MINUTE"] = "1000"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Staff, StaffRole  # noqa: E402
from app.ratelimit import login_limiter, refill_limiter  # noqa: E402
from app.security import hash_password  # noqa: E402

STAFF_EMAIL = "pharmacist@blik.test"
STAFF_PASSWORD = "correct-horse-battery"


@pytest.fixture()
def db_engine():
    """A fresh in-memory SQLite database per test (the real app uses PostgreSQL)."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def client(db_engine):
    session_factory = sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    refill_limiter.reset()
    login_limiter.reset()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def staff_user(db_engine):
    with Session(db_engine) as db:
        db.add(
            Staff(
                email=STAFF_EMAIL,
                password_hash=hash_password(STAFF_PASSWORD),
                role=StaffRole.pharmacist,
            )
        )
        db.commit()
    return {"email": STAFF_EMAIL, "password": STAFF_PASSWORD}


@pytest.fixture()
def auth_headers(client, staff_user):
    response = client.post(
        "/auth/login", data={"username": staff_user["email"], "password": staff_user["password"]}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
