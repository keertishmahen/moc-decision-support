"""
Create Snowflake warehouse MOC_WH, database MOC_DEV, and BRONZE/SILVER/GOLD schemas.

Auth (in order):
  1. SNOWFLAKE_PASSWORD if set
  2. SNOWFLAKE_AUTHENTICATOR=externalbrowser (opens browser SSO)

Usage (from repo root):
  python scripts/bootstrap_snowflake.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

SQL_PATH = _ROOT / "snowflake" / "bootstrap.sql"


def _connect():
    import snowflake.connector

    account = os.getenv("SNOWFLAKE_ACCOUNT", "YOUR_SNOWFLAKE_ACCOUNT")
    user = os.getenv("SNOWFLAKE_USER", "YOUR_SNOWFLAKE_USER")
    role = os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN")
    password = os.getenv("SNOWFLAKE_PASSWORD")
    authenticator = os.getenv("SNOWFLAKE_AUTHENTICATOR", "").strip() or None

    kwargs = {
        "account": account,
        "user": user,
        "role": role,
    }
    if password:
        kwargs["password"] = password
    elif authenticator:
        kwargs["authenticator"] = authenticator
    else:
        kwargs["authenticator"] = "externalbrowser"

    print(f"Connecting to Snowflake account={account} user={user} role={role} ...")
    return snowflake.connector.connect(**kwargs)


def main() -> int:
    sql = SQL_PATH.read_text(encoding="utf-8")
    # Split on semicolons; skip comments-only chunks
    statements = []
    for chunk in sql.split(";"):
        lines = [
            ln for ln in chunk.splitlines()
            if ln.strip() and not ln.strip().startswith("--")
        ]
        stmt = "\n".join(lines).strip()
        if stmt:
            statements.append(stmt)

    conn = _connect()
    try:
        cur = conn.cursor()
        for stmt in statements:
            preview = stmt.replace("\n", " ")[:80]
            print(f"  > {preview}...")
            cur.execute(stmt)
        print("Snowflake bootstrap complete: MOC_WH, MOC_DEV, BRONZE/SILVER/GOLD.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
