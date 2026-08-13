import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from dotenv import load_dotenv

load_dotenv()


# SQLite ulanish URL-manzili (DATABASE_URL env orqali qayta yozish mumkin)
DATABASE_URL = os.getenv("DATABASE_URL")

# SQLite uchun bir nechta thread ishlashi uchun check_same_thread=False kerak
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()