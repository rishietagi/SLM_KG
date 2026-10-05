"""Competency questions (PROJECT_CONTEXT §12) as Cypher over GraphStore.

Each function returns {"question", "rows", "path"} — `path` lists [from_id, rel, to_id] triples so the
viewer can highlight the answer subgraph and tests can assert on it.
"""
from __future__ import annotations

from graph.store import GraphStore

# kuzu 0.11.3 crashes on a $parameter inside a list lambda (any(x IN ... WHERE ...)); bind it with WITH first.
Q1 = """
WITH $term AS term
MATCH (s:ValueChainStage)-[:CONTAINS]->(a:ValueChainActivity)
WHERE lower(a.name) CONTAINS term OR any(x IN a.aliases WHERE lower(x) CONTAINS term)
OPTIONAL MATCH (u:ValueChainStage)-[:PRECEDES]->(s)
OPTIONAL MATCH (s)-[:PRECEDES]->(d:ValueChainStage)
RETURN a.id AS activity_id, a.name AS activity,
       s.id AS stage_id, s.name AS stage, s.stage_number AS stage_number,
       u.id AS upstream_id, u.name AS upstream, d.id AS downstream_id, d.name AS downstream
"""

Q2 = """
MATCH (s3:ValueChainStage {stage_number: $from_stage})-[:CONTAINS]->(a3:ValueChainActivity)
      -[:PRODUCES]->(o:Output)-[:BECOMES_INPUT_TO]->(a4:ValueChainActivity)
      <-[:CONTAINS]-(s4:ValueChainStage {stage_number: $to_stage})
RETURN DISTINCT a3.id AS producer_id, a3.name AS producer, o.id AS output_id, o.name AS output,
       a4.id AS consumer_id, a4.name AS consumer
ORDER BY output, consumer
"""

Q3_DEPENDS = """
WITH $term AS term
MATCH (c:ValueChainActivity) WHERE lower(c.name) CONTAINS term OR any(x IN c.aliases WHERE lower(x) CONTAINS term)
MATCH (a:ValueChainActivity)-[d:DEPENDS_ON]->(c)
MATCH (s:ValueChainStage)-[:CONTAINS]->(a)
RETURN a.id AS activity_id, a.name AS activity, s.name AS stage, c.id AS via_id, 'DEPENDS_ON' AS via
"""

Q3_FEEDS = """
WITH $term AS term
MATCH (c:ValueChainActivity) WHERE lower(c.name) CONTAINS term OR any(x IN c.aliases WHERE lower(x) CONTAINS term)
MATCH (c)-[:PRODUCES]->(o:Output)-[:BECOMES_INPUT_TO]->(a:ValueChainActivity)
MATCH (s:ValueChainStage)-[:CONTAINS]->(a)
RETURN a.id AS activity_id, a.name AS activity, s.name AS stage, o.id AS via_id, 'BECOMES_INPUT_TO' AS via,
       c.id AS producer_id
"""

Q4 = """
MATCH (s:ValueChainStage {stage_number: $stage})-[v:VARIES_IN]->(ss:SubSector)
WHERE ss.id IN $subsectors
RETURN s.id AS element_id, s.name AS element, ss.id AS subsector_id, ss.name AS subsector,
       v.aspect AS aspect, v.variation AS variation
UNION ALL
MATCH (s:ValueChainStage {stage_number: $stage})-[:CONTAINS]->(a:ValueChainActivity)-[v:VARIES_IN]->(ss:SubSector)
WHERE ss.id IN $subsectors
RETURN a.id AS element_id, a.name AS element, ss.id AS subsector_id, ss.name AS subsector,
       v.aspect AS aspect, v.variation AS variation
"""


def cq1(store: GraphStore, term: str = "trade scheme creation") -> dict:
    rows = store.query(Q1, {"term": term.lower()})
    path = []
    for r in rows:
        path.append([r["stage_id"], "CONTAINS", r["activity_id"]])
        if r["upstream_id"]:
            path.append([r["upstream_id"], "PRECEDES", r["stage_id"]])
        if r["downstream_id"]:
            path.append([r["stage_id"], "PRECEDES", r["downstream_id"]])
    return {"question": f'Which stage does "{term}" belong to, and what are its upstream and downstream stages?',
            "rows": rows, "path": path}


def cq2(store: GraphStore, from_stage: int = 3, to_stage: int = 4) -> dict:
    rows = store.query(Q2, {"from_stage": from_stage, "to_stage": to_stage})
    path = []
    for r in rows:
        path += [[r["producer_id"], "PRODUCES", r["output_id"]], [r["output_id"], "BECOMES_INPUT_TO", r["consumer_id"]]]
    return {"question": f"What outputs of Stage {from_stage} become inputs to Stage {to_stage}?",
            "rows": rows, "path": path}


def cq3(store: GraphStore, term: str = "consensus forecast") -> dict:
    params = {"term": term.lower()}
    depends = store.query(Q3_DEPENDS, params)
    feeds = store.query(Q3_FEEDS, params)
    path = [[r["activity_id"], "DEPENDS_ON", r["via_id"]] for r in depends]
    for r in feeds:
        path += [[r["producer_id"], "PRODUCES", r["via_id"]], [r["via_id"], "BECOMES_INPUT_TO", r["activity_id"]]]
    return {"question": f"Which activities depend on the {term}?", "rows": depends + feeds, "path": path}


def cq4(store: GraphStore, stage: int = 5,
        subsectors: tuple[str, ...] = ("SubSector:food_beverage", "SubSector:home_care")) -> dict:
    rows = store.query(Q4, {"stage": stage, "subsectors": list(subsectors)})
    path = [[r["element_id"], "VARIES_IN", r["subsector_id"]] for r in rows]
    return {"question": f"How does Stage {stage} differ between food & beverage and home care?",
            "rows": rows, "path": path}


# ------------------------------------------------------------------ Phase 2 (cross-layer)
Q5 = """
MATCH (s:ValueChainStage {stage_number: $stage})-[:CONTAINS]->(a:ValueChainActivity)-[:ENABLED_BY]->(l:L3ProcessEndpoint)
OPTIONAL MATCH (g:ProcessGroup)-[:CONTAINS]->(l)
OPTIONAL MATCH (d:ProcessArea)-[:CONTAINS]->(g)
RETURN a.id AS activity_id, a.name AS activity, l.id AS endpoint_id, l.name AS endpoint,
       g.id AS group_id, g.name AS process_group, d.id AS area_id, d.name AS process_area
ORDER BY endpoint, activity
"""

def cq5(store: GraphStore, stage: int = 9) -> dict:
    rows = store.query(Q5, {"stage": stage})
    path = []
    for r in rows:
        path.append([r["activity_id"], "ENABLED_BY", r["endpoint_id"]])
        if r["group_id"]:
            path.append([r["group_id"], "CONTAINS", r["endpoint_id"]])
        if r["area_id"]:
            path.append([r["area_id"], "CONTAINS", r["group_id"]])
    return {"question": f"Which L3 processes enable Stage {stage} (outlet execution) activities?",
            "rows": rows, "path": path}


# ------------------------------------------------------------------ intelligence layers (concept level)
Q6_KPI = """
MATCH (s:ValueChainStage {stage_number: $stage})-[:CONTAINS]->(a:ValueChainActivity)-[:CREATES]->(v:ValueOutcome)-[:MEASURED_BY]->(k:KPI)
RETURN a.id AS activity_id, a.name AS activity, v.id AS outcome_id, v.name AS outcome, k.id AS kpi_id, k.name AS kpi
ORDER BY kpi
"""
Q6_RISK = """
MATCH (s:ValueChainStage {stage_number: $stage})-[:CONTAINS]->(a:ValueChainActivity)<-[:AFFECTS]-(r:RiskType)
RETURN r.id AS risk_id, r.name AS risk, a.id AS activity_id, a.name AS activity ORDER BY risk
"""
Q7_CONCEPTS = """
MATCH (s:ValueChainStage {stage_number: $stage})-[:CONTAINS]->(a:ValueChainActivity)-[:ACTS_ON]->(c:ProductAssetConcept)
RETURN a.id AS activity_id, c.id AS concept_id, c.name AS concept, c.concept_group AS concept_group
ORDER BY concept
"""
Q7_EDGES = """
MATCH (x:ProductAssetConcept)-[r]->(y:ProductAssetConcept)
WHERE x.id IN $ids AND y.id IN $ids
RETURN x.id AS from_id, x.name AS from_name, label(r) AS rel, y.id AS to_id, y.name AS to_name
ORDER BY from_name, rel
"""
Q8 = """
MATCH (s:ValueChainStage)-[:CONTAINS]->(a:ValueChainActivity)-[:INVOLVES]->(e:EcosystemConcept)
WHERE s.stage_number >= $first AND s.stage_number <= $last
RETURN e.id AS concept_id, e.name AS concept, e.concept_kind AS kind,
       collect(DISTINCT s.stage_number) AS stages, collect(DISTINCT a.id) AS activity_ids
ORDER BY kind, concept
"""
Q9_TOUCH = """
MATCH (s:ValueChainStage {stage_number: $stage})-[:CONTAINS]->(a:ValueChainActivity)-[:TOUCHES]->(c:ConsumerConcept)
RETURN c.id AS concept_id, c.name AS concept, c.concept_kind AS kind, collect(DISTINCT a.id) AS activity_ids
ORDER BY kind, concept
"""
Q9_TRACE = """
MATCH (c:ConsumerConcept)-[:TRACES_TO_BATCH]->(b:ProductAssetConcept)-[:PRODUCED_AT]->(p:ProductAssetConcept)
WHERE c.id = $concept
OPTIONAL MATCH (c)-[:CONCERNS]->(k:ProductAssetConcept)
RETURN c.id AS complaint_id, b.id AS batch_id, b.name AS batch, p.id AS plant_id, p.name AS plant,
       k.id AS sku_id, k.name AS sku
"""
Q10 = """
MATCH (pa:ProcessArea)-[:CONTAINS]->(g:ProcessGroup)-[:CONTAINS]->(l:L3ProcessEndpoint)<-[:ENABLED_BY]-(a:ValueChainActivity)
      <-[:CONTAINS]-(s:ValueChainStage)
WHERE pa.id = $area
RETURN g.id AS group_id, g.name AS process_group, l.id AS endpoint_id, l.name AS endpoint,
       a.id AS activity_id, a.name AS activity, s.stage_number AS stage, pa.id AS area_id
ORDER BY stage, endpoint
"""


def cq6(store: GraphStore, stage: int = 9) -> dict:
    kpis = store.query(Q6_KPI, {"stage": stage})
    risks = store.query(Q6_RISK, {"stage": stage})
    path = ([[r["activity_id"], "CREATES", r["outcome_id"]] for r in kpis]
            + [[r["outcome_id"], "MEASURED_BY", r["kpi_id"]] for r in kpis]
            + [[r["risk_id"], "AFFECTS", r["activity_id"]] for r in risks])
    rows = ([{"type": "KPI", "name": r["kpi"], "via": f"{r['activity']} -> {r['outcome']}"} for r in kpis]
            + [{"type": "Risk", "name": r["risk"], "via": r["activity"]} for r in risks])
    return {"question": f"Which KPIs measure Stage {stage} outcomes, and which risk types affect those activities?",
            "rows": rows, "path": path, "kpis": sorted({r["kpi"] for r in kpis}),
            "risks": sorted({r["risk"] for r in risks})}


def cq7(store: GraphStore, stage: int = 5) -> dict:
    acts = store.query(Q7_CONCEPTS, {"stage": stage})
    ids = sorted({r["concept_id"] for r in acts})
    edges = store.query(Q7_EDGES, {"ids": ids}) if ids else []
    path = [[r["from_id"], r["rel"], r["to_id"]] for r in edges] + [[r["activity_id"], "ACTS_ON", r["concept_id"]] for r in acts]
    rows = [{"from": r["from_name"], "relationship": r["rel"], "to": r["to_name"]} for r in edges]
    return {"question": f"Which product and asset concepts does Stage {stage} act on, and how do they relate?",
            "rows": rows, "path": path, "concepts": sorted({r["concept"] for r in acts})}


def cq8(store: GraphStore, first: int = 7, last: int = 10) -> dict:
    rows = store.query(Q8, {"first": first, "last": last})
    path = [[a, "INVOLVES", r["concept_id"]] for r in rows for a in r["activity_ids"]]
    return {"question": f"Which ecosystem participants and channels are involved from Stage {first} to Stage {last}?",
            "rows": [{"concept": r["concept"], "kind": r["kind"], "stages": sorted(r["stages"])} for r in rows],
            "path": path}


def cq9(store: GraphStore, stage: int = 10, concept: str = "ConsumerConcept:complaint") -> dict:
    touched = store.query(Q9_TOUCH, {"stage": stage})
    trace = store.query(Q9_TRACE, {"concept": concept})
    path = [[a, "TOUCHES", r["concept_id"]] for r in touched for a in r["activity_ids"]]
    for t in trace:
        path += [[t["complaint_id"], "TRACES_TO_BATCH", t["batch_id"]], [t["batch_id"], "PRODUCED_AT", t["plant_id"]]]
        if t["sku_id"]:
            path.append([t["complaint_id"], "CONCERNS", t["sku_id"]])
    rows = ([{"concept": r["concept"], "kind": r["kind"]} for r in touched]
            + [{"concept": "Complaint traces to", "kind": f"{t['batch']} -> {t['plant']}"
                + (f"; concerns {t['sku']}" if t["sku"] else "")} for t in trace])
    return {"question": f"Which consumer concepts does Stage {stage} touch, and what can a complaint be traced back to?",
            "rows": rows, "path": path, "touched": [r["concept"] for r in touched], "trace": trace}


def cq10(store: GraphStore, area: str = "ProcessArea:trade_promotion_management") -> dict:
    rows = store.query(Q10, {"area": area})
    path = []
    for r in rows:
        path += [[r["area_id"], "CONTAINS", r["group_id"]], [r["group_id"], "CONTAINS", r["endpoint_id"]],
                 [r["activity_id"], "ENABLED_BY", r["endpoint_id"]]]
    label = area.split(":")[1].replace("_", " ")
    return {"question": f"Which L2/L3 processes in {label} enable which activities, across which stages?",
            "rows": [{"process_group": r["process_group"], "l3_process": r["endpoint"], "activity": r["activity"],
                      "stage": r["stage"]} for r in rows], "path": path}


ALL = {1: cq1, 2: cq2, 3: cq3, 4: cq4, 5: cq5, 6: cq6, 7: cq7, 8: cq8, 9: cq9, 10: cq10}
