"""Curated reference data conformance: models, allowed pairs, provenance, id resolution, stage chain."""
from __future__ import annotations

from pydantic import ValidationError

from codegen.loader import ROOT, Ontology
from pipeline.reference import ReferenceData, class_of, edge_record, node_record

REQUIRED_PROVENANCE = ("source_system", "source_reference", "extraction_confidence", "lane", "reviewed")


def check_reference(onto: Ontology, data: ReferenceData) -> list[str]:
    from gen.models import NODE_MODELS, Edge

    errors = list(data.errors)
    for node_id, row in data.nodes.items():
        where = f"{row['_file']} {node_id}"
        cls = row["_class"]
        if cls not in onto.classes:
            errors.append(f"{where}: undeclared class {cls}")
            continue
        if class_of(node_id) != cls:
            errors.append(f"{where}: id prefix must be '{cls}:'")
        errors += _provenance(where, row)
        try:
            NODE_MODELS[cls].model_validate(node_record(row))
        except ValidationError as e:
            errors += [f"{where}: {_fmt(err)}" for err in e.errors()]

    for e in data.edges:
        where = f"{e['_file']} {e['from_id']} -[{e['relationship']}]-> {e['to_id']}"
        if e["relationship"] not in onto.relationships:
            errors.append(f"{where}: undeclared relationship")
            continue
        missing = [i for i in (e["from_id"], e["to_id"]) if i not in data.nodes]
        if missing:
            errors.append(f"{where}: unknown node id(s) {missing}")
            continue
        errors += _provenance(where, e)
        try:
            Edge.model_validate(edge_record(e))
        except ValidationError as err:
            errors += [f"{where}: {_fmt(x)}" for x in err.errors()]

    errors += _stage_chain(data)
    return errors


def _provenance(where: str, row: dict) -> list[str]:
    errs = [f"{where}: missing provenance field {k}" for k in REQUIRED_PROVENANCE if row.get(k) in (None, "")]
    ref = row.get("source_reference")
    if ref:
        path = ref.split("#", 1)[0]
        if not (ROOT / path).exists():
            errs.append(f"{where}: source_reference points to missing file {path}")
    if row.get("lane") == "curated" and row.get("extraction_confidence") not in (None, 1.0, 1):
        errs.append(f"{where}: curated rows use extraction_confidence 1.0")
    return errs


def _stage_chain(data: ReferenceData) -> list[str]:
    """Denormalised upstream/downstream_stage must agree with PRECEDES."""
    errors = []
    nxt = {e["from_id"]: e["to_id"] for e in data.edges if e["relationship"] == "PRECEDES"}
    prev = {v: k for k, v in nxt.items()}
    for node_id, row in data.nodes.items():
        if row["_class"] != "ValueChainStage":
            continue
        if row.get("downstream_stage") != nxt.get(node_id):
            errors.append(f"{node_id}: downstream_stage {row.get('downstream_stage')} != PRECEDES {nxt.get(node_id)}")
        if row.get("upstream_stage") != prev.get(node_id):
            errors.append(f"{node_id}: upstream_stage {row.get('upstream_stage')} != PRECEDES {prev.get(node_id)}")
    return errors


def _fmt(err: dict) -> str:
    loc = ".".join(str(x) for x in err.get("loc", ()))
    return f"{loc}: {err.get('msg')}" if loc else str(err.get("msg"))
