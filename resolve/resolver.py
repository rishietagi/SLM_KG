"""`make resolve`: accepted staging records -> canonical entities and edges (PROJECT_CONTEXT §10.2 step 5).

Order: exact source id -> alias table / master names -> fuzzy match (difflib >= 0.92) -> review queue.
Matching is always within one class, so do-not-merge pairs (different classes) can never merge.
Duplicates from several sources merge with the structured lane taking priority; every other name or label
is kept in `aliases`. Anchor edges (reference/rules/anchor_rules.yaml) tie instances to the spine.
"""
from __future__ import annotations

import difflib
from collections import Counter, defaultdict
from dataclasses import dataclass, field

import yaml

from codegen.loader import ROOT, load_ontology
from pipeline.staging import RESOLVED, REVIEW, source, write_jsonl
from pipeline.staging import REJECTED, read_jsonl
from validate.staging_checks import check_core, check_staging

RULES = ROOT / "reference" / "rules"
FUZZY_CUTOFF = 0.92
# Classes whose instances must already exist as masters / transactions in the structured lane.
MASTER_CLASSES = {"Brand", "Category", "ProductFamily", "SKU", "Customer", "Distributor", "Retailer", "Outlet",
                  "Channel", "Geography", "FiscalPeriod", "Currency", "TradePromotion", "SalesInvoice", "SalesOrder",
                  "PackPricePoint", "ConsumerSegment", "NeedState"}


@dataclass
class Resolution:
    entities: dict[str, dict] = field(default_factory=dict)
    edges: list[dict] = field(default_factory=list)
    review: list[dict] = field(default_factory=list)
    rejected: list[dict] = field(default_factory=list)
    stats: Counter = field(default_factory=Counter)


def _priority(rec: dict) -> int:
    return 0 if rec["source"]["source_system"].startswith("synthetic_") else 1


def _norm(s: str | None) -> str:
    return " ".join(str(s or "").lower().replace("_", " ").split())


# Same-priority sources disagreeing on a status: keep the furthest-progressed one (D46).
STATUS_RANK = {"submitted": 0, "received": 0, "open": 0, "pending": 1, "approved": 2, "partially_approved": 2,
               "rejected": 2, "posted": 2, "settled": 3, "closed": 3}


def resolve(entities: list[dict], relationships: list[dict], onto=None) -> Resolution:
    res = Resolution()
    aliases_cfg = yaml.safe_load((RULES / "aliases.yaml").read_text(encoding="utf-8"))["aliases"]

    known: dict[str, set[str]] = defaultdict(set)  # class -> ids from the structured lane
    names: dict[str, dict[str, str]] = defaultdict(dict)  # class -> normalized name/code -> id
    for e in entities:
        if _priority(e) == 0:
            cls, eid = e["entity_type"], e["entity_id"]
            known[cls].add(eid)
            for label in (e["name"], e.get("source_label"), eid.split(":", 1)[1]):
                names[cls].setdefault(_norm(label), eid)
    for cls, table in aliases_cfg.items():
        for eid, variants in table.items():
            for v in [eid.split(":", 1)[1], *variants]:
                names[cls][_norm(v)] = eid

    mapping: dict[str, str | None] = {}
    for e in entities:
        cls, eid = e["entity_type"], e["entity_id"]
        if eid in mapping or eid in known[cls]:
            mapping.setdefault(eid, eid)
            res.stats["exact"] += _priority(e)
            continue
        candidates = [_norm(eid.split(":", 1)[1]), _norm(e["name"]), _norm(e.get("source_label"))]
        hit = next((names[cls][c] for c in candidates if c in names[cls]), None)
        if hit:
            mapping[eid] = hit
            res.stats["alias"] += 1
            continue
        fuzzy = difflib.get_close_matches(_norm(e["name"]), list(names[cls]), n=1, cutoff=FUZZY_CUTOFF)
        if fuzzy:
            mapping[eid] = names[cls][fuzzy[0]]
            res.stats["fuzzy"] += 1
            continue
        if cls in MASTER_CLASSES:
            mapping[eid] = None
            res.review.append({"reason": f"no {cls} master matches", "record": e})
            res.stats["review"] += 1
            continue
        mapping[eid] = eid  # a new fact (claim, credit note, evidence, ...)
        res.stats["new"] += 1

    # merge duplicates: highest-priority record wins; others fill gaps and contribute aliases
    groups: dict[str, list[dict]] = defaultdict(list)
    for e in entities:
        target = mapping.get(e["entity_id"])
        if target:
            groups[target].append(e)
    for eid, recs in groups.items():
        recs.sort(key=_priority)
        primary = recs[0]
        attrs = dict(primary.get("attributes", {}))
        labels = set()
        for r in recs:
            labels |= {r["name"], r.get("source_label") or r["name"]}
            for k, v in r.get("attributes", {}).items():
                if k not in attrs:
                    attrs[k] = v
                elif attrs[k] != v and not k.endswith("_text"):
                    res.stats["attribute_conflicts"] += 1
                    if k == "status" and _priority(r) == _priority(primary) and                             STATUS_RANK.get(str(v), -1) > STATUS_RANK.get(str(attrs[k]), -1):
                        attrs[k] = v
        merged = {**primary, "entity_id": eid, "attributes": attrs,
                  "aliases": sorted(lbl for lbl in labels if lbl and lbl != primary["name"])}
        if len(recs) > 1:
            res.stats["merged"] += 1
        res.entities[eid] = merged

    seen = set()
    for r in sorted(relationships, key=_priority):
        s, o = mapping.get(r["subject_id"], r["subject_id"]), mapping.get(r["object_id"], r["object_id"])
        if s is None or o is None or s not in res.entities or o not in res.entities:
            res.review.append({"reason": "relationship endpoint unresolved or missing", "record": r})
            res.stats["review_edges"] += 1
            continue
        key = (r["relationship"], s, o)
        if key in seen:
            res.stats["duplicate_edges"] += 1
            continue
        seen.add(key)
        res.edges.append({**r, "subject_id": s, "object_id": o})

    if onto is not None:  # §4 core constraints on merged entities; violators and their edges leave the graph
        bad = check_core(onto, res.entities, res.edges)
        for eid, reasons in bad.items():
            res.rejected.append({"file": "resolved", "reasons": reasons, "record": res.entities.pop(eid)})
        if bad:
            kept = [e for e in res.edges if e["subject_id"] not in bad and e["object_id"] not in bad]
            res.stats["edges_dropped_with_rejected"] += len(res.edges) - len(kept)
            res.edges = kept
        res.stats["rejected_core"] = len(bad)

    rules = yaml.safe_load((RULES / "anchor_rules.yaml").read_text(encoding="utf-8"))["rules"]
    by_class = defaultdict(list)
    for eid, e in res.entities.items():
        by_class[e["entity_type"]].append(eid)
    for rule in rules:
        src = source("anchor_rules", rule["class"], "reference/rules/anchor_rules.yaml")
        for eid in by_class.get(rule["class"], []):
            res.edges.append({"kind": "relationship", "subject_type": "ValueChainActivity", "subject_id": rule["from"],
                              "relationship": rule["relationship"], "object_type": rule["class"], "object_id": eid,
                              "attributes": {}, "source": src})
            res.stats["anchor_edges"] += 1
    return res


def run() -> int:
    onto = load_ontology()
    st = check_staging(onto)
    res = resolve(st.entities, st.relationships, onto)
    for d in (RESOLVED, REVIEW):
        for old in d.glob("*.jsonl"):
            old.unlink()
    write_jsonl(RESOLVED / "entities.jsonl", res.entities.values())
    write_jsonl(RESOLVED / "edges.jsonl", res.edges)
    write_jsonl(REVIEW / "review.jsonl", res.review)
    write_jsonl(REJECTED / "rejected.jsonl", [*read_jsonl(REJECTED / "rejected.jsonl"), *res.rejected]
                if (REJECTED / "rejected.jsonl").exists() else res.rejected)
    s = res.stats
    print(f"resolve: {len(res.entities)} entities, {len(res.edges)} edges ({s['anchor_edges']} anchors); "
          f"llm matches exact={s['exact']} alias={s['alias']} fuzzy={s['fuzzy']} new={s['new']}; merged={s['merged']}; "
          f"review={s['review']} entities + {s['review_edges']} edges; conflicts={s['attribute_conflicts']}; "
          f"core-constraint rejected={s['rejected_core']}")
    return 0
