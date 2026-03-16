from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.infrastructure.config.settings import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()
