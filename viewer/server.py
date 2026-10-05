"""Graph and schema viewer: `make viewer` -> http://127.0.0.1:8000

Read-only. All graph access goes through GraphStore. Stop the viewer before `make load` (DB file lock).
"""
from __future__ import annotations

import json
import os
import threading
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from codegen.loader import ROOT
from graph.store import GraphStore, open_store
from pipeline.load import DB_PATH
from pipeline.report import collect
from retrieve.competency import ALL as COMPETENCY

STATIC = Path(__file__).parent / "static"
INDEX = ROOT / "gen" / "ontology_index.json"
DB = Path(os.environ.get("KG_DB", DB_PATH))
PROVENANCE = {"source_system", "source_record_id", "source_reference", "extraction_confidence", "lane",
              "reviewed", "drafted_beyond_source", "review_note"}

app = FastAPI(title="CPG Intelligence Graph viewer")
_lock = threading.Lock()
_store: GraphStore | None = None


def store() -> GraphStore:
    global _store
    if _store is None:
        if not DB.exists():
            raise HTTPException(503, "No database yet: run `make load`.")
        _store = open_store(DB, read_only=True)
    return _store


def q(cypher: str, params: dict | None = None) -> list[dict]:
    with _lock:
        return store().query(cypher, params)


@lru_cache(maxsize=1)
def ontology_index() -> dict:
    return json.loads(INDEX.read_text(encoding="utf-8"))


def _clean(props: dict) -> dict:
    return {k: v for k, v in props.items()
            if not k.startswith("_") and v not in (None, [], "") and not k.endswith("_text")}


@app.get("/api/schema")
def schema() -> dict:
    idx = ontology_index()
    try:
        counts = {r["cls"]: r["n"] for r in q("MATCH (n) RETURN label(n) AS cls, count(*) AS n")}
    except HTTPException:
        counts = {}
    return {**idx, "instance_counts": counts}


# High-volume instance classes stay out of the initial graph; reach them with /api/expand (D47).
HEAVY = ["SellOutTransaction", "AvailabilityObservation", "PurchaseEvent", "InvoiceLine", "InventoryPosition",
         "DemandForecast", "SalesOrder", "SalesInvoice", "Margin"]


def _layer(cls: str) -> int:
    return ontology_index()["classes"].get(cls, {}).get("layer", 0)


@app.get("/api/graph")
def graph() -> dict:
    nodes = q("MATCH (n) WHERE NOT label(n) IN $heavy RETURN n.id AS id, label(n) AS cls, n.name AS name, "
              "n.reviewed AS reviewed, n.drafted_beyond_source AS drafted, n.lane AS lane", {"heavy": HEAVY})
    for n in nodes:
        n["layer"] = _layer(n["cls"])
    seq = {r["id"]: r for r in q("MATCH (a:ValueChainActivity) RETURN a.id AS id, a.sequence AS sequence")}
    stages = {r["id"]: r["n"] for r in q("MATCH (s:ValueChainStage) RETURN s.id AS id, s.stage_number AS n")}
    for n in nodes:
        if n["id"] in seq:
            n["sequence"] = seq[n["id"]]["sequence"]
        if n["id"] in stages:
            n["stage_number"] = stages[n["id"]]
    edges = q("MATCH (a)-[r]->(b) WHERE NOT label(a) IN $heavy AND NOT label(b) IN $heavy "
              "RETURN a.id AS source, b.id AS target, label(r) AS rel, r.drafted_beyond_source AS drafted",
              {"heavy": HEAVY})
    for i, e in enumerate(edges):
        e["id"] = f"e{i}"
    counts = {r["cls"]: r["n"] for r in q("MATCH (n) WHERE label(n) IN $heavy RETURN label(n) AS cls, count(*) AS n",
                                          {"heavy": HEAVY})}
    return {"nodes": nodes, "edges": edges, "hidden_counts": counts}


@app.get("/api/expand/{node_id:path}")
def expand(node_id: str, limit: int = 30) -> dict:
    """Neighbours of one node (up to `limit` per relationship and direction) as graph elements."""
    cls = node_id.split(":", 1)[0]
    if cls not in ontology_index()["classes"]:
        raise HTTPException(404, f"unknown class {cls}")
    out = q(f"MATCH (n:{cls})-[r]->(m) WHERE n.id = $id RETURN label(r) AS rel, m.id AS id, m.name AS name, "
            "label(m) AS cls, m.lane AS lane, r.drafted_beyond_source AS drafted, 'out' AS dir", {"id": node_id})
    inc = q(f"MATCH (m)-[r]->(n:{cls}) WHERE n.id = $id RETURN label(r) AS rel, m.id AS id, m.name AS name, "
            "label(m) AS cls, m.lane AS lane, r.drafted_beyond_source AS drafted, 'in' AS dir", {"id": node_id})
    seen: dict[tuple, int] = {}
    nodes, edges, truncated = {}, [], {}
    for r in out + inc:
        key = (r["rel"], r["dir"])
        seen[key] = seen.get(key, 0) + 1
        if seen[key] > limit:
            truncated[f"{r['dir']} {r['rel']}"] = seen[key]
            continue
        nodes[r["id"]] = {"id": r["id"], "cls": r["cls"], "name": r["name"], "lane": r["lane"], "layer": _layer(r["cls"])}
        src, dst = (node_id, r["id"]) if r["dir"] == "out" else (r["id"], node_id)
        edges.append({"id": f"x:{src}|{r['rel']}|{dst}", "source": src, "target": dst, "rel": r["rel"],
                      "drafted": r["drafted"]})
    return {"nodes": list(nodes.values()), "edges": edges, "truncated": truncated}


@app.get("/api/node/{node_id:path}")
def node(node_id: str) -> dict:
    cls = node_id.split(":", 1)[0]
    if cls not in ontology_index()["classes"]:
        raise HTTPException(404, f"unknown class {cls}")
    rows = q(f"MATCH (n:{cls}) WHERE n.id = $id RETURN n", {"id": node_id})
    if not rows:
        raise HTTPException(404, f"no node {node_id}")
    props = _clean(rows[0]["n"])
    out = q(f"MATCH (n:{cls})-[r]->(m) WHERE n.id = $id "
            "RETURN label(r) AS rel, m.id AS id, m.name AS name, label(m) AS cls, r AS r", {"id": node_id})
    inc = q(f"MATCH (m)-[r]->(n:{cls}) WHERE n.id = $id "
            "RETURN label(r) AS rel, m.id AS id, m.name AS name, label(m) AS cls, r AS r", {"id": node_id})
    edge_meta = {"source_system", "source_record_id", "source_reference", "extraction_confidence", "lane", "reviewed"}

    def nb(rows: list[dict], direction: str, cap: int = 12) -> list[dict]:
        kept, per = [], {}
        for r in rows:
            per[r["rel"]] = per.get(r["rel"], 0) + 1
            if per[r["rel"]] <= cap:
                kept.append({"rel": r["rel"], "id": r["id"], "name": r["name"], "cls": r["cls"], "direction": direction,
                             "props": {k: v for k, v in _clean(r["r"]).items() if k not in edge_meta}})
        for rel, n in per.items():
            if n > cap:
                kept.append({"rel": rel, "id": None, "name": f"… and {n - cap} more", "cls": "", "direction": direction,
                             "props": {}})
        return kept

    return {
        "id": node_id, "cls": cls,
        "class_info": ontology_index()["classes"][cls],
        "properties": {k: v for k, v in props.items() if k not in PROVENANCE},
        "provenance": {k: v for k, v in props.items() if k in PROVENANCE},
        "neighbors": nb(out, "out") + nb(inc, "in"),
    }


@app.get("/api/competency/{n}")
def competency(n: int) -> dict:
    if n not in COMPETENCY:
        raise HTTPException(404, f"competency questions {sorted(COMPETENCY)} are implemented")
    with _lock:
        return COMPETENCY[n](store())


@app.get("/api/report")
def report() -> dict:
    with _lock:
        m = collect(store())
    return {**m, "orphans_by_lane": dict(m["orphans_by_lane"]), "nodes_by_lane": dict(m["nodes_by_lane"]),
            "edges_by_rel": dict(m["edges_by_rel"]),
            "per_class": {c: {"nodes": n, "edges_per_node": round(a, 2)} for c, (n, a) in m["per_class"].items()}}


@app.get("/docs-src/{path:path}", response_class=PlainTextResponse)
def doc_source(path: str) -> str:
    """Serve cited source documents (docs/ only) so provenance links open."""
    target = (ROOT / "docs" / path).resolve()
    if not target.is_relative_to((ROOT / "docs").resolve()) or not target.is_file():
        raise HTTPException(404)
    return target.read_text(encoding="utf-8")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
