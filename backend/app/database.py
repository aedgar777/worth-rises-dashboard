from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


def _build_engine():
    if settings.use_cloud_sql_connector:
        from google.cloud.sql.connector import Connector

        connector = Connector()

        def getconn():
            return connector.connect(
                settings.cloud_sql_instance,
                "pg8000",
                user=settings.db_user,
                password=settings.db_pass,
                db=settings.db_name,
            )

        return create_engine(
            "postgresql+pg8000://",
            creator=getconn,
            pool_pre_ping=True,
        )

    return create_engine(settings.database_url, pool_pre_ping=True)


engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_migrations() -> None:
    """Apply incremental schema updates (safe to run on every startup)."""
    with engine.begin() as conn:
        conn.execute(
            text("ALTER TABLE matched_rates ADD COLUMN IF NOT EXISTS place_id VARCHAR(255)")
        )
        conn.execute(
            text("ALTER TABLE matched_rates ADD COLUMN IF NOT EXISTS place_description TEXT")
        )
        conn.execute(
            text("ALTER TABLE matched_rates ADD COLUMN IF NOT EXISTS facility_rules TEXT")
        )
        conn.execute(
            text("ALTER TABLE provider_facilities ADD COLUMN IF NOT EXISTS facility_address TEXT")
        )


def init_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    run_migrations()
