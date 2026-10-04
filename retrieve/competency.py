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


ALL = {1: cq1, 2: cq2, 3: cq3, 4: cq4}
