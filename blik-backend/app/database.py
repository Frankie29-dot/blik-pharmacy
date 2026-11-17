from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# hide_parameters=True stops SQLAlchemy from putting bound values (phone numbers,
# prescription numbers) into exception messages and therefore into error logs.
# Never set echo=True in production for the same reason.
engine = create_engine(settings.database_url, pool_pre_ping=True, hide_parameters=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
