import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base


# Use absolute path for database to ensure it works in all environments
# Check if we're in Render environment
if os.environ.get('RENDER'):
    # In Render, use the current working directory
    DATABASE_PATH = os.path.join(os.getcwd(), "internships.db")
else:
    # Local development
    DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "internships.db")

DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DATABASE_PATH}")

print(f"Database URL: {DATABASE_URL}")
print(f"Database path: {DATABASE_PATH}")
if os.path.exists(DATABASE_PATH):
    print("Database file exists")
else:
    print("Database file does NOT exist")

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
    from models import Offer, User, ScrapingStat  # noqa: F401
    Base.metadata.create_all(bind=engine)
    print("Database initialized")