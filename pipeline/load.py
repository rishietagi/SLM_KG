"""`make load`: rebuild the graph database from scratch — DDL, then COPY FROM parquet. Never row-by-row."""
from __future__ import annotations

import shutil
from pathlib import Path

from codegen.loader import ROOT, load_ontology
from graph.store import GraphStore, get_store
from pipeline.curated import PARQUET_DIR, write_parquet

DB_PATH = ROOT / "db" / "cpg.kuzu"
DDL_PATH = ROOT / "gen" / "ddl" / "schema.cypher"


def _remove_db(path: Path) -> None:
    for p in (path, path.with_name(path.name + ".wal"), path.with_name(path.name + ".lock")):
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()


def build_database(db_path: Path = DB_PATH, parquet_dir: Path = PARQUET_DIR) -> GraphStore:
    """Fresh database with the full schema and all curated data. Returns an open store."""
    onto = load_ontology()
    parquet = write_parquet(onto, parquet_dir)
    _remove_db(db_path)
    store = get_store().connect(db_path)
    store.apply_ddl(DDL_PATH)
    for table, path in parquet.nodes:
        store.bulk_load_parquet(table, path)
    for rel, f, t, path in parquet.edges:
        multi = len(onto.relationships[rel].pairs) > 1
        store.bulk_load_parquet(rel, path, f if multi else None, t if multi else None)
    return store


def run() -> None:
    store = build_database()
    try:
        n = store.query("MATCH (n) RETURN count(n) AS c")[0]["c"]
        e = store.query("MATCH ()-[r]->() RETURN count(r) AS c")[0]["c"]
        print(f"load: {n} nodes, {e} edges into {DB_PATH.relative_to(ROOT).as_posix()}")
    finally:
        store.close()
