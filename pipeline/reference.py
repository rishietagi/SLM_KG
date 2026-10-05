"""Read curated reference data (reference/*.yaml, reference/edges/*.yaml) into node and edge rows.

Node file:  {class: <Class>, defaults: {...}, edge_defaults: {REL: {...}},
             rows: [{id, name, ..., edges: {REL: [id | {to: id, prop: v}]}}],
             groups: [{defaults: {...}, rows: [...]}]}      # groups layer extra defaults over file defaults
Edge file:  {relationship: <REL>, defaults: {...}, rows: [{from: id, to: id, prop: v, ...}]}
IDs are `<Class>:<slug>` (PROJECT_CONTEXT §4), so an id alone resolves its node table.
Edge provenance defaults to the provenance of the row that declares it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from codegen.loader import ROOT

REFERENCE_DIR = ROOT / "reference"
EDGE_PROVENANCE = ("source_system", "source_record_id", "source_reference", "extraction_confidence",
                   "lane", "reviewed", "drafted_beyond_source")


@dataclass
class ReferenceData:
    nodes: dict[str, dict] = field(default_factory=dict)  # id -> row (incl. "_class", "_file")
    edges: list[dict] = field(default_factory=list)  # {relationship, from_id, to_id, from_type, to_type, ...}
    errors: list[str] = field(default_factory=list)


def class_of(node_id: str) -> str:
    return node_id.split(":", 1)[0]


def load_reference(directory: Path = REFERENCE_DIR) -> ReferenceData:
    data = ReferenceData()
    for path in sorted(directory.glob("*.yaml")) + sorted((directory / "layers").glob("*.yaml")):
        _load_node_file(path, data)
    for path in sorted((directory / "edges").glob("*.yaml")):
        _load_edge_file(path, data)
    for e in data.edges:
        e["from_type"], e["to_type"] = class_of(e["from_id"]), class_of(e["to_id"])
    return data


def _read(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _load_node_file(path: Path, data: ReferenceData) -> None:
    doc = _read(path)
    cls, defaults = doc.get("class"), doc.get("defaults", {})
    edge_defaults = doc.get("edge_defaults", {})
    if not cls:
        data.errors.append(f"{_rel(path)}: missing `class`")
        return
    batches = [(defaults, doc.get("rows", []))]
    batches += [({**defaults, **g.get("defaults", {})}, g.get("rows", [])) for g in doc.get("groups", [])]
    for batch_defaults, rows in batches:
        _load_rows(path, cls, batch_defaults, edge_defaults, rows, data)


def _load_rows(path: Path, cls: str, defaults: dict, edge_defaults: dict, rows: list, data: ReferenceData) -> None:
    for raw in rows:
        row = {**defaults, **raw}
        row.pop("edges", None)
        edges: dict[str, list] = {}
        for src in (defaults.get("edges") or {}, raw.get("edges") or {}):  # group edges merge into row edges
            for rel, targets in src.items():
                edges.setdefault(rel, []).extend(targets or [])
        node_id = row.get("id")
        if not node_id:
            data.errors.append(f"{_rel(path)}: row without id: {raw}")
            continue
        if node_id in data.nodes:
            data.errors.append(f"{_rel(path)}: duplicate id {node_id}")
        row["_class"], row["_file"] = cls, _rel(path)
        data.nodes[node_id] = row
        prov = {k: row[k] for k in EDGE_PROVENANCE if k in row}
        for rel, targets in edges.items():
            for t in targets or []:
                spec = {"to": t} if isinstance(t, str) else dict(t)
                to_id = spec.pop("to")
                data.edges.append({"relationship": rel, "from_id": node_id, "to_id": to_id,
                                   **prov, **edge_defaults.get(rel, {}), **spec, "_file": _rel(path)})


def _load_edge_file(path: Path, data: ReferenceData) -> None:
    doc = _read(path)
    rel, defaults = doc.get("relationship"), doc.get("defaults", {})
    if not rel:
        data.errors.append(f"{_rel(path)}: missing `relationship`")
        return
    for raw in doc.get("rows", []):
        row = {**defaults, **raw}
        data.edges.append({"relationship": rel, "from_id": row.pop("from"), "to_id": row.pop("to"),
                           **row, "_file": _rel(path)})


def node_record(row: dict) -> dict:
    """Row without loader bookkeeping keys."""
    return {k: v for k, v in row.items() if not k.startswith("_")}


def edge_record(edge: dict) -> dict:
    return {k: v for k, v in edge.items() if not k.startswith("_")}
