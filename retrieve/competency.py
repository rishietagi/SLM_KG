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
OPTIONAL MATCH (d:FinanceDomain)-[:CONTAINS]->(g)
RETURN a.id AS activity_id, a.name AS activity, l.id AS endpoint_id, l.name AS endpoint,
       g.id AS group_id, g.name AS process_group, d.id AS domain_id, d.name AS domain
ORDER BY endpoint, activity
"""

# Window = promotion period; baseline = the equal-length period immediately before it.
Q6_PRIMARY = """
MATCH (p:TradePromotion)-[:TARGETS]->(c:Customer)-[:ACCOUNT_OF]->(d:Distributor)
MATCH (c)<-[:ISSUED_TO]-(i:SalesInvoice)-[:CONTAINS]->(l:InvoiceLine)-[:REFERENCES]->(k:SKU)<-[:APPLIES_TO]-(p)
WITH p, l.quantity AS q, i.invoice_date AS dt, p.start_date AS s, p.end_date AS e
RETURN p.id AS promotion_id, p.name AS promotion,
       sum(CASE WHEN dt >= s AND dt <= e THEN q ELSE 0.0 END) AS promo_qty,
       sum(CASE WHEN dt >= s - (e - s) - interval("1 day") AND dt < s THEN q ELSE 0.0 END) AS base_qty
"""

Q6_SELL_OUT = """
MATCH (p:TradePromotion)-[:TARGETS]->(c:Customer)-[:ACCOUNT_OF]->(d:Distributor)-[:SERVES]->(o:Outlet)
MATCH (o)<-[:OCCURS_AT]-(t:SellOutTransaction)-[:REFERENCES]->(k:SKU)<-[:APPLIES_TO]-(p)
WITH p, t.quantity AS q, t.week_start AS dt, p.start_date AS s, p.end_date AS e
RETURN p.id AS promotion_id,
       sum(CASE WHEN dt >= s AND dt <= e THEN q ELSE 0.0 END) AS promo_qty,
       sum(CASE WHEN dt >= s - (e - s) - interval("1 day") AND dt < s THEN q ELSE 0.0 END) AS base_qty
"""

Q6_PATH = """
MATCH (p:TradePromotion)-[:TARGETS]->(c:Customer)-[:ACCOUNT_OF]->(d:Distributor)
WHERE p.id IN $ids
OPTIONAL MATCH (p)-[:APPLIES_TO]->(k:SKU)
RETURN p.id AS p, c.id AS c, d.id AS d, collect(DISTINCT k.id) AS skus
"""

Q7 = """
MATCH (cl:PromotionClaim)-[:CLAIMED_AGAINST]->(p:TradePromotion)
WHERE p.id = $promotion
OPTIONAL MATCH (cl)-[:SUBMITTED_BY]->(c:Customer)
OPTIONAL MATCH (cl)-[:REFERENCES]->(inv:SalesInvoice)
OPTIONAL MATCH (cl)-[:REFERENCES]->(k:SKU)
OPTIONAL MATCH (cn:CreditNote)-[:SETTLES]->(cl)
OPTIONAL MATCH (ps:PromotionSettlement)-[:SETTLES]->(cl)
RETURN cl.id AS claim_id, cl.claim_amount AS claimed, cl.approved_amount AS approved, cl.currency AS currency,
       cl.status AS status, c.id AS customer_id, inv.id AS invoice_id, k.id AS sku_id,
       cn.id AS credit_note_id, cn.amount AS credit_note_amount, ps.id AS settlement_id, ps.amount AS settlement_amount,
       cl.source_reference AS source_reference
ORDER BY claim_id
"""


def cq5(store: GraphStore, stage: int = 9) -> dict:
    rows = store.query(Q5, {"stage": stage})
    path = []
    for r in rows:
        path.append([r["activity_id"], "ENABLED_BY", r["endpoint_id"]])
        if r["group_id"]:
            path.append([r["group_id"], "CONTAINS", r["endpoint_id"]])
        if r["domain_id"]:
            path.append([r["domain_id"], "CONTAINS", r["group_id"]])
    return {"question": f"Which finance L3 processes enable Stage {stage} (outlet execution) activities?",
            "rows": rows, "path": path}


def _uplift(promo: float, base: float) -> float | None:
    return None if not base else promo / base - 1


def cq6(store: GraphStore, min_primary_uplift: float = 0.30, max_sell_out_uplift: float = 0.10) -> dict:
    primary = {r["promotion_id"]: r for r in store.query(Q6_PRIMARY)}
    sell = {r["promotion_id"]: r for r in store.query(Q6_SELL_OUT)}
    rows = []
    for pid, r in sorted(primary.items()):
        so = sell.get(pid, {"promo_qty": 0.0, "base_qty": 0.0})
        pu, su = _uplift(r["promo_qty"], r["base_qty"]), _uplift(so["promo_qty"], so["base_qty"])
        flagged = pu is not None and su is not None and pu >= min_primary_uplift and su <= max_sell_out_uplift
        rows.append({"promotion_id": pid, "promotion": r["promotion"],
                     "primary_uplift": round(pu, 3) if pu is not None else None,
                     "sell_out_uplift": round(su, 3) if su is not None else None,
                     "loaded_without_sell_through": flagged})
    flagged_ids = [r["promotion_id"] for r in rows if r["loaded_without_sell_through"]]
    path = []
    for r in store.query(Q6_PATH, {"ids": flagged_ids}) if flagged_ids else []:
        path += [[r["p"], "TARGETS", r["c"]], [r["c"], "ACCOUNT_OF", r["d"]]]
        path += [[r["p"], "APPLIES_TO", k] for k in r["skus"]]
    return {"question": "Which trade promotions loaded distributors but did not produce outlet sell-through?",
            "rows": rows, "path": path, "flagged": flagged_ids}


def cq7(store: GraphStore, promotion: str = "TradePromotion:TP2026-005") -> dict:
    rows = store.query(Q7, {"promotion": promotion})
    path = []
    for r in rows:
        path.append([r["claim_id"], "CLAIMED_AGAINST", promotion])
        for rel_, key in (("SUBMITTED_BY", "customer_id"), ("REFERENCES", "invoice_id"), ("REFERENCES", "sku_id")):
            if r[key]:
                path.append([r["claim_id"], rel_, r[key]])
        for key in ("credit_note_id", "settlement_id"):
            if r[key]:
                path.append([r[key], "SETTLES", r["claim_id"]])
    return {"question": f"For promotion {promotion.split(':')[1]}, what was claimed, approved and settled, "
                        "against which invoices and SKUs?", "rows": rows, "path": path}


ALL = {1: cq1, 2: cq2, 3: cq3, 4: cq4, 5: cq5, 6: cq6, 7: cq7}
