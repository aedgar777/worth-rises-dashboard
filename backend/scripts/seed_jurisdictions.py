#!/usr/bin/env python3
"""Seed the jurisdictions Cloud SQL database from the assignment CSV."""

from pathlib import Path
import sys

from app.jurisdictions_db import init_jurisdictions_db, seed_jurisdictions_from_csv

DEFAULT_PATHS = [
    Path("/home/andreweedgar/Downloads/2026.07 - Staff Technologist Data Test (for applicant) v2 - Jurisdictions to Match.csv"),
    Path(__file__).resolve().parent.parent / "data" / "jurisdictions-to-match.csv",
    Path(__file__).resolve().parent.parent / "sample-data" / "jurisdictions-to-match.csv",
]


def main() -> None:
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if csv_path is None:
        for candidate in DEFAULT_PATHS:
            if candidate.exists():
                csv_path = candidate
                break

    if csv_path is None or not csv_path.exists():
        print("Jurisdictions CSV not found. Pass path as first argument.")
        sys.exit(1)

    init_jurisdictions_db()
    count = seed_jurisdictions_from_csv(csv_path)
    print(f"Seeded {count} jurisdictions from {csv_path}")


if __name__ == "__main__":
    main()
