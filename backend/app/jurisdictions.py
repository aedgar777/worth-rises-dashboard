import pandas as pd
from sqlalchemy.orm import Session

from app.jurisdiction_model import Jurisdiction


def load_jurisdictions(db: Session) -> pd.DataFrame:
    rows = (
        db.query(Jurisdiction)
        .order_by(Jurisdiction.state, Jurisdiction.county)
        .all()
    )
    if not rows:
        raise RuntimeError(
            "Jurisdictions database is empty. Run seed_jurisdictions_from_csv or "
            "apply infra/jurisdictions_schema.sql with seed data."
        )
    return pd.DataFrame(
        [
            {
                "type": r.jurisdiction_type,
                "state": r.state,
                "county": r.county,
            }
            for r in rows
        ]
    )


def jurisdiction_count(db: Session) -> int:
    return db.query(Jurisdiction).count()
