import os
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Base para ORM
Base = declarative_base()


# Modelos
class Scan(Base):
    __tablename__ = "scans"
    id = Column(Integer, primary_key=True, index=True)
    input_url = Column(String, nullable=False)
    normalized_url = Column(String, nullable=False)
    score = Column(Integer, nullable=False)
    verdict = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Signal(Base):
    __tablename__ = "scan_signals"
    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    value = Column(String, nullable=False)


class Report(Base):
    __tablename__ = "scan_reports"
    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, nullable=False)
    summary = Column(String, nullable=False)
    recommendations = Column(String, nullable=False)
    confidence_notes = Column(String, nullable=True)


# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Crear tablas
Base.metadata.create_all(bind=engine)
