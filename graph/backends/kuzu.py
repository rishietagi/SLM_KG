"""Kuzu backend, pinned to kuzu==0.11.3. Never copy DB files across engines; rebuild from parquet."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import kuzu

from graph.store import GraphStore

PINNED = "0.11.3"


class KuzuStore(GraphStore):
    def __init__(self) -> None:
        if kuzu.__version__ != PINNED:
            raise RuntimeError(f"kuzu {PINNED} required, found {kuzu.__version__}")
        self._db: kuzu.Database | None = None
        self._conn: kuzu.Connection | None = None

    def connect(self, path: str | Path, read_only: bool = False) -> "KuzuStore":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = kuzu.Database(str(path), read_only=read_only)
        self._conn = kuzu.Connection(self._db)
        return self

    def query(self, cypher: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if self._conn is None:
            raise RuntimeError("not connected")
        result = self._conn.execute(cypher, params or {})
        cols = result.get_column_names()
        rows = []
        while result.has_next():
            rows.append(dict(zip(cols, result.get_next())))
        return rows

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
        if self._db is not None:
            self._db.close()
        self._conn = self._db = None
