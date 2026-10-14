import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def _db_url() -> str:
    url = os.getenv("DATABASE_URL", "sqlite:///./shortlink.db")
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return url.replace(prefix, "postgresql+psycopg2://", 1)
    return url


URL = _db_url()
engine = create_engine(
    URL,
    connect_args={"check_same_thread": False} if URL.startswith("sqlite") else {},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
