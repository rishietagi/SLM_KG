"""`make report`: quality metrics from the loaded database (PROJECT_CONTEXT §10.3)."""
from __future__ import annotations

from collections import Counter, defaultdict

from codegen.loader import ROOT, load_ontology
from graph.store import GraphStore, get_store
from pipeline.load import DB_PATH
from validate.orphans import find_orphans


def collect(store: GraphStore) -> dict:
    onto = load_ontology()
    nodes = store.query("MATCH (n) RETURN n.id AS id, label(n) AS cls, n.lane AS lane, "
                        "n.reviewed AS reviewed, n.drafted_beyond_source AS drafted")
    edges = store.query("MATCH (a)-[r]->(b) RETURN a.id AS a, b.id AS b, label(r) AS rel, "
                        "r.drafted_beyond_source AS drafted")
    classes = {n["id"]: n["cls"] for n in nodes}
    lanes = {n["id"]: n["lane"] for n in nodes}
    orphans = find_orphans(classes, [(e["a"], e["b"]) for e in edges])

    degree: Counter = Counter()
    for e in edges:
        degree[e["a"]] += 1
        degree[e["b"]] += 1
    per_class: dict[str, list[int]] = defaultdict(list)
    for nid, cls in classes.items():
        per_class[cls].append(degree[nid])

    # outer layer = any class with layer > 1; path to a ValueChainActivity via the spine
    outer = [i for i, c in classes.items() if onto.classes[c].layer > 1]
    outer_reachable = [i for i in outer if i not in set(orphans)]

    staging = ROOT / "staging"
    return {
        "nodes": len(nodes),
        "edges": len(edges),
        "orphans": orphans,
        "orphans_by_lane": Counter(lanes[o] for o in orphans),
        "nodes_by_lane": Counter(lanes.values()),
        "per_class": {c: (len(d), sum(d) / len(d)) for c, d in sorted(per_class.items())},
        "edges_by_rel": Counter(e["rel"] for e in edges),
        "outer": (len(outer_reachable), len(outer)),
        "unreviewed_nodes": sum(1 for n in nodes if not n["reviewed"]),
        "drafted_nodes": sum(1 for n in nodes if n["drafted"]),
        "drafted_edges": sum(1 for e in edges if e["drafted"]),
        "rejected": sum(1 for p in (staging / "rejected").glob("*") if p.name != ".gitkeep"),
        "unresolved": sum(1 for p in (staging / "unresolved").glob("*") if p.name != ".gitkeep"),
    }


def render(m: dict) -> str:
    curated = m["nodes_by_lane"].get("curated", 0)
    curated_orphans = m["orphans_by_lane"].get("curated", 0)
    extracted = m["nodes_by_lane"].get("extracted", 0)
    lines = [
        "CPG Intelligence Graph - quality report",
        "=" * 60,
        f"nodes {m['nodes']}  edges {m['edges']}  (curated {curated}, extracted {extracted})",
        "",
        f"orphans, curated lane      : {curated_orphans} / {curated}   (target 0)",
        f"orphans, extracted lane    : {m['orphans_by_lane'].get('extracted', 0)} / {extracted}   (target < 5%)",
        f"outer-layer nodes reaching a ValueChainActivity: {m['outer'][0]} / {m['outer'][1]}"
        + ("   (no outer-layer instances until Phase 2)" if m["outer"][1] == 0 else ""),
        f"validation rejections      : {m['rejected']}",
        f"unresolved items           : {m['unresolved']}",
        f"awaiting review            : {m['unreviewed_nodes']} nodes; drafted beyond source: "
        f"{m['drafted_nodes']} nodes, {m['drafted_edges']} edges",
        "",
        f"{'class':<22}{'nodes':>7}{'edges/node':>12}",
        "-" * 41,
    ]
    lines += [f"{c:<22}{n:>7}{avg:>12.2f}" for c, (n, avg) in m["per_class"].items()]
    lines += ["", f"{'relationship':<24}{'edges':>7}", "-" * 31]
    lines += [f"{r:<24}{n:>7}" for r, n in sorted(m["edges_by_rel"].items())]
    if m["orphans"]:
        lines += ["", "orphan nodes:"] + [f"  {o}" for o in m["orphans"]]
    return "\n".join(lines)


def run() -> int:
    if not DB_PATH.exists():
        print("no database: run `make load` first")
        return 1
    store = get_store().connect(DB_PATH, read_only=True)
    try:
        m = collect(store)
    finally:
        store.close()
    print(render(m))
    return 1 if m["orphans_by_lane"].get("curated", 0) else 0
