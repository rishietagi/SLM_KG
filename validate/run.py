"""`make validate`: ontology integrity + reference data + orphans + staging. Non-zero exit on any error."""
from __future__ import annotations

from collections import Counter

from codegen.loader import ROOT, OntologyError, load_ontology
from pipeline.reference import load_reference
from validate.ontology_checks import check_ontology
from validate.orphans import find_orphans
from validate.reference_checks import check_reference


def run() -> int:
    failed = False

    def section(title: str, errors: list[str]) -> None:
        nonlocal failed
        status = "OK" if not errors else f"FAIL ({len(errors)})"
        print(f"[{status}] {title}")
        for e in errors[:50]:
            print(f"    - {e}")
        if len(errors) > 50:
            print(f"    ... {len(errors) - 50} more")
        failed |= bool(errors)

    try:
        onto = load_ontology()
    except (OntologyError, ValueError) as e:
        section("ontology loads", [str(e)])
        return 1
    errors = check_ontology(onto)
    undeclared = [e for e in errors if e.startswith("undeclared class")]
    section(f"ontology integrity - {len(onto.classes)} classes, {len(onto.relationships)} relationships, "
            f"{len(undeclared)} undeclared classes", errors)
    if any("gen/ is stale" in e for e in errors):
        return 1
    used = {c for _, f, t in onto.pair_set() for c in (f, t)}
    isolated = sorted(c for c in onto.classes if c not in used)
    if isolated:
        # Not an error until instances exist: any instance of these would be an orphan (DECISIONS D36).
        print(f"warn: {len(isolated)} classes have no relationships: {', '.join(isolated)}")

    data = load_reference()
    section(f"reference data - {len(data.nodes)} nodes, {len(data.edges)} edges", check_reference(onto, data))

    classes = {i: r["_class"] for i, r in data.nodes.items()}
    orphans = find_orphans(classes, [(e["from_id"], e["to_id"]) for e in data.edges if e["to_id"] in classes])
    section(f"orphans (curated lane) - {len(orphans)}", [f"{o} ({classes[o]})" for o in orphans])

    staged = [p for p in (ROOT / "staging").rglob("*") if p.is_file() and p.name != ".gitkeep"]
    section(f"staging - {len(staged)} files (extraction lane starts in Phase 2)", [])

    drafted = sum(1 for r in data.nodes.values() if r.get("drafted_beyond_source"))
    unreviewed = sum(1 for r in data.nodes.values() if not r.get("reviewed"))
    by_class = Counter(classes.values())
    print(f"info: {unreviewed} rows awaiting review, {drafted} drafted beyond source; "
          + ", ".join(f"{k}={v}" for k, v in sorted(by_class.items())))
    print("validate: " + ("FAILED" if failed else "green"))
    return 1 if failed else 0
