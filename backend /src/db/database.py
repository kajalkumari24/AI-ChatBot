from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import settings
from src.db.base import Base

DATABASE_URL = settings.DATABASE_URL or "sqlite:///./chatbot.db"

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency — yields a DB session, closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Creates all tables. Imports every model so Base knows about all tables."""
    from src.models import user, conversation  # noqa: F401
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    print("Using DATABASE_URL:", DATABASE_URL)
    init_db()
    print("Tables created successfully.")
    print("database.py OK")
