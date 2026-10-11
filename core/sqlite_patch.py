"""Patch stdlib sqlite3 when the runtime ships an older version (ChromaDB needs >= 3.35)."""


def patch_sqlite() -> None:
    import sqlite3
    import sys

    if sqlite3.sqlite_version_info >= (3, 35, 0):
        return
    try:
        import pysqlite3  # type: ignore
    except ImportError:
        return
    sys.modules["sqlite3"] = pysqlite3


patch_sqlite()
