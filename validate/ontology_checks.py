"""Ontology integrity: declared classes, layers, naming, forbidden relationships, name map, gen freshness."""
from __future__ import annotations

from collections import defaultdict

import yaml

from codegen.loader import ONTOLOGY_DIR, ROOT, Ontology, ontology_hash
from codegen.meta import PASCAL, SNAKE, UPPER_SNAKE, ModuleFile


def check_ontology(onto: Ontology) -> list[str]:
    errors: list[str] = []
    classes = onto.classes

    # every class has a layer and description; naming conventions
    for name, c in classes.items():
        if not PASCAL.match(name):
            errors.append(f"class {name}: not PascalCase")
        if not 1 <= c.layer <= 6:
            errors.append(f"class {name}: layer {c.layer} outside 1..6")
        if not c.description.strip():
            errors.append(f"class {name}: empty description")
        for attr in c.attributes:
            if not SNAKE.match(attr):
                errors.append(f"{name}.{attr}: attribute not snake_case")
            if attr in onto.common.node_base:
                errors.append(f"{name}.{attr}: redeclares a node_base attribute")
        if c.stub and c.module != "hooks":
            errors.append(f"class {name}: stub classes belong in hooks.yaml")
    for attr in list(onto.common.node_base) + list(onto.common.edge_base):
        if not SNAKE.match(attr):
            errors.append(f"common.{attr}: not snake_case")

    # naming drift: classes equal ignoring case/underscores
    folded = defaultdict(list)
    for name in classes:
        folded[name.lower().replace("_", "")].append(name)
    errors += [f"naming drift: {v}" for v in folded.values() if len(v) > 1]

    # relationships
    for rel, d in onto.relationships.items():
        if not UPPER_SNAKE.match(rel):
            errors.append(f"relationship {rel}: not UPPER_SNAKE_CASE")
        if rel in onto.common.forbidden_relationships:
            errors.append(f"relationship {rel}: generic relationship forbidden (CLAUDE.md rule 4)")
        for prop in d.properties:
            if not SNAKE.match(prop):
                errors.append(f"{rel}.{prop}: property not snake_case")
        for p in d.pairs:
            for end in (p.from_, p.to):
                if end not in classes:
                    errors.append(f"undeclared class {end} in {rel} ({p.from_}->{p.to})")
            if p.from_ == "Category" and p.to == "Brand":
                errors.append(f"{rel}: Category->Brand is forbidden (CLAUDE.md rule 12)")
        if d.hook_layer is None and "hooks" in d.modules:
            errors.append(f"hook {rel}: missing hook_layer")

    # do-not-merge pairs must stay distinct classes when both are declared
    for a, b in onto.common.do_not_merge:
        if a == b:
            errors.append(f"do_not_merge pair {a}/{b} is degenerate")

    errors += _check_rel_map(onto)

    # slices only reference declared classes/relationships
    if onto.slices:
        for name, sl in onto.slices.slices.items():
            errors += [f"slice {name}: undeclared class {c}" for c in sl.classes if c not in classes]
            errors += [f"slice {name}: undeclared relationship {r}" for r in sl.relationships
                       if r not in onto.relationships]

    # gen/ freshness
    stamp = ROOT / "gen" / ".ontology_hash"
    current = ontology_hash()
    if not stamp.exists() or stamp.read_text(encoding="utf-8").strip() != current:
        errors.append("gen/ is stale: run `make gen`")
    return errors


def _check_rel_map(onto: Ontology) -> list[str]:
    errors: list[str] = []
    rm = onto.rel_map
    if rm is None:
        return ["ontology/rel_name_map.yaml missing"]
    pairs = onto.pair_set()
    produced: set[tuple[str, str, str]] = set()
    for e in rm.entries:
        if e.action in ("dropped", "deferred"):
            if e.canonical is not None:
                errors.append(f"rel_name_map: {e.original} {e.from_}->{e.to} is {e.action} but has a canonical name")
            continue
        if e.canonical is None:
            errors.append(f"rel_name_map: {e.original} {e.from_}->{e.to} has no canonical name")
            continue
        key = (e.canonical, e.canonical_from or e.from_, e.canonical_to or e.to)
        if key not in pairs:
            errors.append(f"rel_name_map: {e.original} maps to undeclared pair {key}")
        produced.add(key)
        if e.action == "converted" and e.canonical != _upper(e.original):
            errors.append(f"rel_name_map: {e.original} -> {e.canonical} is not a mechanical conversion; use `renamed`")
    for a in rm.added:
        produced.add((a["canonical"], a["from"], a["to"]))

    finance = ModuleFile.model_validate(yaml.safe_load((ONTOLOGY_DIR / "finance.yaml").read_text(encoding="utf-8")))
    for rel, d in finance.relationships.items():
        for p in d.pairs:
            if (rel, p.from_, p.to) not in produced:
                errors.append(f"finance.yaml pair {rel} {p.from_}->{p.to} not traceable in rel_name_map.yaml")
    return errors


def _upper(camel: str) -> str:
    out = []
    for i, ch in enumerate(camel):
        if ch.isupper() and i and not camel[i - 1].isupper():
            out.append("_")
        out.append(ch.upper())
    return "".join(out)
