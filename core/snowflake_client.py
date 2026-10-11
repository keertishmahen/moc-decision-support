"""Shared Snowflake connection helpers (password or externalbrowser)."""
from __future__ import annotations

import os
from typing import Any

import snowflake.connector
from snowflake.connector import DictCursor


def snowflake_connect_kwargs() -> dict[str, Any]:
    password = os.getenv("SNOWFLAKE_PASSWORD")
    authenticator = (os.getenv("SNOWFLAKE_AUTHENTICATOR") or "").strip() or None
    kwargs: dict[str, Any] = {
        "account": os.getenv("SNOWFLAKE_ACCOUNT", "YOUR_SNOWFLAKE_ACCOUNT"),
        "user": os.getenv("SNOWFLAKE_USER", "YOUR_SNOWFLAKE_USER"),
        "role": os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "MOC_WH"),
        "database": os.getenv("SNOWFLAKE_DATABASE", "MOC_DEV"),
    }
    if password:
        kwargs["password"] = password
    elif authenticator:
        kwargs["authenticator"] = authenticator
    else:
        kwargs["authenticator"] = "externalbrowser"
    return kwargs


def connect():
    return snowflake.connector.connect(**snowflake_connect_kwargs())


def fetch_all(sql: str) -> list[dict[str, Any]]:
    conn = connect()
    try:
        cur = conn.cursor(DictCursor)
        cur.execute(sql)
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
