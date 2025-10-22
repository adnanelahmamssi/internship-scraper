import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    # SQLite file in project directory by default
    f"sqlite:///" + os.path.join(os.path.dirname(__file__), "internships.db"),
)


# For SQLite, need check_same_thread=False for multithreaded scheduler access
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=True,
    echo=False,  # Set to True for SQL debugging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db_session():
    return SessionLocal()


def init_db():
    from models import Offer, User  # noqa: F401
    Base.metadata.create_all(bind=engine)