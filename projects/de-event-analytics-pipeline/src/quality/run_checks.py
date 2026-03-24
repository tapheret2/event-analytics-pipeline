from __future__ import annotations

from pathlib import Path

from src.common.db import connect

ROOT = Path(__file__).resolve().parents[2]
CHECKS = ROOT / "src" / "quality" / "checks.sql"


def main():
    sql = CHECKS.read_text(encoding="utf-8")
    statements = [s.strip() for s in sql.split(";") if s.strip()]

    failures = 0
    with connect() as conn:
        with conn.cursor() as cur:
            for i, st in enumerate(statements, 1):
                cur.execute(st)
                rows = cur.fetchall()
                if rows:
                    failures += 1
                    print(f"FAIL check #{i}: returned {len(rows)} rows")

    if failures:
        raise SystemExit(f"FAILED: {failures} checks")

    print("OK: all checks passed")


if __name__ == "__main__":
    main()
