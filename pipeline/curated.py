"""Curated lane: reference YAML -> typed parquet (one file per node table and per rel FROM-TO pair)."""
from __future__ import annotations

import datetime
import shutil
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from codegen.generate import columns
from codegen.loader import ROOT, Ontology, load_ontology
from pipeline.reference import load_reference

PARQUET_DIR = ROOT / "build" / "parquet"

ARROW = {
    "STRING": pa.string(), "INT64": pa.int64(), "DOUBLE": pa.float64(), "BOOLEAN": pa.bool_(),
    "DATE": pa.date32(), "TIMESTAMP": pa.timestamp("us"), "STRING[]": pa.list_(pa.string()),
}


@dataclass
class ParquetSet:
    nodes: list[tuple[str, Path]] = field(default_factory=list)  # (table, file)
    edges: list[tuple[str, str, str, Path]] = field(default_factory=list)  # (rel, from, to, file)


def _coerce(value, ddl_type: str):
    if value is None:
        # kuzu 0.11.3 list lambdas (any(x IN l WHERE ...)) leak the previous row's result when l is NULL;
        # store empty lists instead (DECISIONS D31).
        return [] if ddl_type == "STRING[]" else None
    if ddl_type == "DATE" and isinstance(value, str):
        return datetime.date.fromisoformat(value)
    if ddl_type == "STRING" and not isinstance(value, str):
        return str(value)
    if ddl_type == "DOUBLE":
        return float(value)
    return value


def _table(rows: list[dict], cols: list[tuple[str, str]], lead: list[tuple[str, str]] = ()) -> pa.Table:
    allcols = list(lead) + cols
    arrays = [pa.array([_coerce(r.get(c), t) for r in rows], type=ARROW[t]) for c, t in allcols]
    return pa.Table.from_arrays(arrays, names=[c for c, _ in allcols])


def write_parquet(onto: Ontology | None = None, out_dir: Path = PARQUET_DIR) -> ParquetSet:
    onto = onto or load_ontology()
    data = load_reference()
    if data.errors:
        raise ValueError("reference data has errors; run `make validate`")
    shutil.rmtree(out_dir, ignore_errors=True)
    (out_dir / "nodes").mkdir(parents=True)
    (out_dir / "edges").mkdir(parents=True)
    result = ParquetSet()

    by_class: dict[str, list[dict]] = defaultdict(list)
    for row in data.nodes.values():
        by_class[row["_class"]].append(row)
    for cls, rows in sorted(by_class.items()):
        path = out_dir / "nodes" / f"{cls}.parquet"
        pq.write_table(_table(rows, columns(onto, onto.node_attributes(cls))), path)
        result.nodes.append((cls, path))

    by_pair: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for e in data.edges:
        by_pair[(e["relationship"], e["from_type"], e["to_type"])].append(
            {**e, "from": e["from_id"], "to": e["to_id"]})
    for (rel, f, t), rows in sorted(by_pair.items()):
        path = out_dir / "edges" / f"{rel}__{f}__{t}.parquet"
        lead = [("from", "STRING"), ("to", "STRING")]
        pq.write_table(_table(rows, columns(onto, onto.edge_properties(rel)), lead), path)
        result.edges.append((rel, f, t, path))
    return result
