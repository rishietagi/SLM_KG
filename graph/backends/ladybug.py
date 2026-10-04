"""LadybugDB backend (`real_ladybug`, the community fork of Kuzu). Same API as kuzu.

Not installed in the mmsa env yet (DECISIONS D1); importing this module fails with a clear message.
Ladybug may not open Kuzu database files — always rebuild from parquet.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import real_ladybug as lb
except ImportError as e:  # pragma: no cover - exercised only when ladybug is absent
    raise ImportError("real_ladybug is not installed; set KG_BACKEND=kuzu or `pip install real_ladybug`") from e

from graph.store import GraphStore


class LadybugStore(GraphStore):
    def __init__(self) -> None:
        self._db = None
        self._conn = None

    def connect(self, path: str | Path, read_only: bool = False) -> "LadybugStore":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = lb.Database(str(path), read_only=read_only)
        self._conn = lb.Connection(self._db)
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
