from __future__ import annotations

import os
import psycopg2


def conn_params() -> dict:
    return {
        "host": os.getenv("PGHOST", "localhost"),
        "port": int(os.getenv("PGPORT", "5432")),
        "dbname": os.getenv("PGDATABASE", "analytics"),
        "user": os.getenv("PGUSER", "de"),
        "password": os.getenv("PGPASSWORD", "de"),
    }


def connect():
    return psycopg2.connect(**conn_params())
