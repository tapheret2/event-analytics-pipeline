from __future__ import annotations

import sys
from pathlib import Path

from src.common.db import connect


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python run_sql.py <file.sql>")

    sql_path = Path(sys.argv[1])
    sql = sql_path.read_text(encoding="utf-8")

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()

    print(f"OK: executed {sql_path}")


if __name__ == "__main__":
    main()
