from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.settings import Settings


DATABASE_URL = Settings().database_url
connect_args = {"check_same_thread": False} if make_url(DATABASE_URL).get_backend_name() == "sqlite" else {}
if make_url(DATABASE_URL).get_backend_name() == "postgresql":
    connect_args["connect_timeout"] = 5
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True, hide_parameters=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
