"""Engine-agnostic graph access. Only graph/backends/* import a graph engine (CLAUDE.md rule 9)."""
from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

DEFAULT_BACKEND = "kuzu"  # DECISIONS D1: kuzu 0.11.3 active in the mmsa env; ladybug when installed


class GraphStore(ABC):
    """Minimal interface the pipeline, validators, tests and viewer use."""

    @abstractmethod
    def connect(self, path: str | Path, read_only: bool = False) -> "GraphStore": ...

    @abstractmethod
    def query(self, cypher: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]: ...

    @abstractmethod
    def close(self) -> None: ...

    def apply_ddl(self, ddl: str | Path) -> int:
        """Run each `;`-terminated statement; `//` comment lines are ignored. Returns statement count."""
        text = Path(ddl).read_text(encoding="utf-8") if isinstance(ddl, Path) else ddl
        text = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("//"))
        stmts = [s.strip() for s in text.split(";") if s.strip()]
        for s in stmts:
            self.query(s)
        return len(stmts)

    def bulk_load_parquet(
        self, table: str, path: str | Path, from_label: str | None = None, to_label: str | None = None
    ) -> None:
        """COPY FROM a parquet file. Rel tables with several FROM-TO pairs need from/to labels."""
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table):
            raise ValueError(f"bad table name {table!r}")
        p = Path(path).resolve().as_posix()
        opts = f" (from='{from_label}', to='{to_label}')" if from_label and to_label else ""
        self.query(f"COPY {table} FROM '{p}'{opts}")

    def __enter__(self) -> "GraphStore":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def get_store(backend: str | None = None) -> GraphStore:
    name = (backend or os.environ.get("KG_BACKEND") or DEFAULT_BACKEND).lower()
    if name == "kuzu":
        from graph.backends.kuzu import KuzuStore

        return KuzuStore()
    if name == "ladybug":
        from graph.backends.ladybug import LadybugStore

        return LadybugStore()
    raise ValueError(f"unknown graph backend {name!r}")


def open_store(path: str | Path, read_only: bool = False, backend: str | None = None) -> GraphStore:
    return get_store(backend).connect(path, read_only=read_only)
