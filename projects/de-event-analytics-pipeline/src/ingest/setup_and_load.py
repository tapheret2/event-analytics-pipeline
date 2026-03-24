from __future__ import annotations

from pathlib import Path
import pandas as pd

from src.common.db import connect

ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT / "data" / "raw" / "events.csv"

SCHEMA_SQL = """
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS stg;
CREATE SCHEMA IF NOT EXISTS marts;

DROP TABLE IF EXISTS raw.events;
CREATE TABLE raw.events (
  event_time TIMESTAMP NOT NULL,
  user_id BIGINT,
  event_name TEXT NOT NULL,
  country TEXT,
  device TEXT,
  revenue NUMERIC
);
"""


def main():
    if not CSV_PATH.exists():
        raise SystemExit(f"Missing {CSV_PATH}")

    df = pd.read_csv(CSV_PATH)
    # basic cleanup
    df["event_time"] = pd.to_datetime(df["event_time"])

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
        conn.commit()

        # load
        with conn.cursor() as cur:
            for row in df.itertuples(index=False):
                cur.execute(
                    "INSERT INTO raw.events(event_time,user_id,event_name,country,device,revenue) VALUES (%s,%s,%s,%s,%s,%s)",
                    (row.event_time, row.user_id if pd.notna(row.user_id) else None, row.event_name, row.country, row.device, row.revenue if pd.notna(row.revenue) else None),
                )
        conn.commit()

    print("OK: loaded", len(df), "rows into raw.events")


if __name__ == "__main__":
    main()
