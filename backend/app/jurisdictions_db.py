from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class JurisdictionsBase(DeclarativeBase):
    pass


def _build_jurisdictions_engine():
    if settings.use_cloud_sql_connector:
        from google.cloud.sql.connector import Connector

        connector = Connector()
        db_name = settings.jurisdictions_db_name

        def getconn():
            return connector.connect(
                settings.cloud_sql_instance,
                "pg8000",
                user=settings.db_user,
                password=settings.db_pass,
                db=db_name,
            )

        return create_engine(
            "postgresql+pg8000://",
            creator=getconn,
            pool_pre_ping=True,
        )

    base_url = settings.database_url.rsplit("/", 1)[0]
    return create_engine(
        f"{base_url}/{settings.jurisdictions_db_name}",
        pool_pre_ping=True,
    )


jurisdictions_engine = _build_jurisdictions_engine()
JurisdictionsSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=jurisdictions_engine
)


def get_jurisdictions_db() -> Generator[Session, None, None]:
    db = JurisdictionsSessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_jurisdictions_db() -> None:
    from app import jurisdiction_model  # noqa: F401

    JurisdictionsBase.metadata.create_all(bind=jurisdictions_engine)


SEED_CSV = Path(__file__).resolve().parent.parent / "data" / "jurisdictions-to-match.csv"


def seed_jurisdictions_from_csv(csv_path: Path | None = None) -> int:
    """Load jurisdictions CSV into the jurisdictions database if the table is empty."""
    import pandas as pd

    from app.jurisdiction_model import Jurisdiction

    path = csv_path or SEED_CSV
    if not path.exists():
        return 0

    db = JurisdictionsSessionLocal()
    try:
        if db.query(Jurisdiction).count() > 0:
            return 0

        df = pd.read_csv(path)
        df.columns = [c.strip().lower() for c in df.columns]
        inserted = 0
        for _, row in df.iterrows():
            county_val = row.get("county")
            county = None
            if county_val is not None and str(county_val).strip() and str(county_val) != "nan":
                county = str(county_val).strip()
            db.add(
                Jurisdiction(
                    jurisdiction_type=str(row["type"]).lower().strip(),
                    state=str(row["state"]).upper().strip(),
                    county=county,
                )
            )
            inserted += 1
        db.commit()
        return inserted
    finally:
        db.close()
