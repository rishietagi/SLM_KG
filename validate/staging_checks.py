"""Extracted-lane validation (PROJECT_CONTEXT §10.2 step 4; DECISIONS D44).

Per record (record -> staging/rejected/): undeclared class or relationship, disallowed pair, missing
id/name/provenance, wrong attribute types. Missing spec-"required" attributes are only warnings.
The finance spec §4 core constraints run on the *resolved* entity (`check_core`), because one fact can
be spread over several documents (a claim letter states the amount; the credit note states approval).
unresolved records -> staging/unresolved/.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from pydantic import ValidationError

from codegen.loader import Ontology
from pipeline.staging import EXTRACTED, REJECTED, UNRESOLVED, read_dir, write_jsonl

PROVENANCE = ("source_system", "source_record_id", "source_reference", "extraction_confidence")

# finance spec §4 attribute constraints, canonical names
CORE_ATTRS = {
    "PromotionClaim": ["claim_amount", "status"],
    "TradePromotion": ["start_date", "end_date"],
    "JournalLine": ["amount", "debit_credit_indicator", "currency"],
    "KPI": ["business_definition", "formula", "unit"],
    "Control": ["owner", "frequency", "control_type"],
    "Variance": ["variance_type", "value", "unit"],
    "Budget": ["version"],
    "Forecast": ["version"],
}
# §4.10: every financial amount needs a currency
AMOUNT_NEEDS_CURRENCY = {"amount", "claim_amount", "approved_amount", "sales_value", "spend"}
# §4 relationship constraints: class -> [(relationship, target classes, direction)]
CORE_EDGES = {
    "PromotionClaim": [("SUBMITTED_BY", {"Customer"}), ("CLAIMED_AGAINST", {"TradePromotion"})],
    "TradePromotion": [({"APPLIES_TO", "TARGETS", "EXECUTED_IN", "BELONGS_TO"}, {"SKU", "Brand", "Customer", "Channel"})],
}


@dataclass
class StagingResult:
    entities: list[dict] = field(default_factory=list)
    relationships: list[dict] = field(default_factory=list)
    rejected: list[dict] = field(default_factory=list)
    unresolved: list[dict] = field(default_factory=list)
    warnings: Counter = field(default_factory=Counter)
    reasons: Counter = field(default_factory=Counter)
    total: int = 0


def node_row(rec: dict) -> dict:
    """Staging entity -> flat node row (Pydantic model / parquet shape)."""
    return {"id": rec["entity_id"], "name": rec["name"], "source_label": rec.get("source_label"),
            "description": rec.get("description"), **rec.get("attributes", {}), **rec["source"],
            "lane": "extracted", "reviewed": False}


def edge_row(rec: dict) -> dict:
    return {"relationship": rec["relationship"], "from_type": rec["subject_type"], "from_id": rec["subject_id"],
            "to_type": rec["object_type"], "to_id": rec["object_id"], **rec.get("attributes", {}), **rec["source"],
            "lane": "extracted", "reviewed": False}


def check_staging(onto: Ontology, write: bool = True) -> StagingResult:
    from gen.models import NODE_MODELS, Edge

    res = StagingResult()
    staged: list[tuple[str, dict]] = list(read_dir(EXTRACTED))
    res.total = len(staged)

    def reject(rec: dict, file: str, reasons: list[str]) -> None:
        res.rejected.append({"file": file, "reasons": reasons, "record": rec})
        res.reasons.update(r.split(":")[0] for r in reasons)

    for file, rec in staged:
        kind = rec.get("kind")
        if kind == "unresolved":
            res.unresolved.append({"file": file, **rec})
            continue
        src = rec.get("source") or {}
        missing_prov = [k for k in PROVENANCE if src.get(k) in (None, "")]
        if kind == "entity":
            cls = rec.get("entity_type")
            if cls not in onto.classes:
                reject(rec, file, [f"undeclared class: {cls}"])
                continue
            reasons = [f"missing provenance: {k}" for k in missing_prov]
            if not rec.get("entity_id") or not rec.get("name"):
                reasons.append("missing id or name: ")
            try:
                NODE_MODELS[cls].model_validate(node_row(rec))
            except ValidationError as e:
                for err in e.errors():
                    loc = ".".join(str(x) for x in err["loc"])
                    if err["type"] == "missing":
                        res.warnings[f"{cls}.{loc} missing"] += 1  # spec-required but not stated: warn only
                    else:
                        reasons.append(f"invalid attribute: {loc} {err['msg']}")
            if reasons:
                reject(rec, file, reasons)
            else:
                res.entities.append(rec)
        elif kind == "relationship":
            rel = rec.get("relationship")
            if rel not in onto.relationships:
                reject(rec, file, [f"undeclared relationship: {rel}"])
                continue
            reasons = [f"missing provenance: {k}" for k in missing_prov]
            try:
                Edge.model_validate(edge_row(rec))
            except ValidationError as e:
                reasons += [f"invalid relationship: {err['msg']}" for err in e.errors()]
            if reasons:
                reject(rec, file, reasons)
            else:
                res.relationships.append(rec)
        else:
            reject(rec, file, [f"unknown record kind: {kind}"])

    if write:
        for d in (REJECTED, UNRESOLVED):
            for old in d.glob("*.jsonl"):
                old.unlink()
        write_jsonl(REJECTED / "rejected.jsonl", res.rejected)
        write_jsonl(UNRESOLVED / "unresolved.jsonl", res.unresolved)
    return res


def check_core(onto: Ontology, entities: dict[str, dict], edges: list[dict]) -> dict[str, list[str]]:
    """Finance spec §4 core constraints on resolved entities. Returns {entity_id: reasons} for violations."""
    out = defaultdict(set)
    for r in edges:
        out[r["subject_id"]].add((r["relationship"], r["object_type"]))
    bad: dict[str, list[str]] = {}
    for eid, e in entities.items():
        cls, attrs = e["entity_type"], e.get("attributes", {})
        reasons = [f"§4 constraint: {cls}.{a} required" for a in CORE_ATTRS.get(cls, []) if attrs.get(a) in (None, "")]
        if (set(attrs) & AMOUNT_NEEDS_CURRENCY) and "currency" in onto.classes[cls].attributes and not attrs.get("currency"):
            reasons.append(f"§4 constraint: {cls} amount without currency")
        for rels, targets in CORE_EDGES.get(cls, []):
            rels = {rels} if isinstance(rels, str) else rels
            if not any(r in rels and t in targets for r, t in out[eid]):
                reasons.append(f"§4 constraint: {cls} needs {'/'.join(sorted(rels))} -> {'/'.join(sorted(targets))}")
        if reasons:
            bad[eid] = reasons
    return bad
