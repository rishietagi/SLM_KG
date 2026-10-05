"""Extraction prompts: kg-extraction skill rules + the routed slice's catalogue (classes, attributes, pairs)."""
from __future__ import annotations

from codegen.loader import Ontology

RULES = """You are a knowledge-graph extraction engine for the Consumer Markets (CPG) sector.
Extract ONLY entities and relationships that are explicitly stated in the text, using the catalogue below.

Rules:
1. Explicit only. Do not infer, assume or complete missing facts. If something is ambiguous, put it in
   unresolved_items with the source text and the reason; do not force a relationship.
2. Never calculate, rescale or modify amounts. Give the number exactly as stated without thousands
   separators or currency (e.g. "620000"), put the currency in a separate `currency` attribute, and the
   verbatim text in `<attribute>_text` (e.g. claim_amount_text = "INR 620,000").
3. entity_id is the identifier exactly as written in the source (e.g. "CLM8421", "D107", "TP2026-005",
   "BW-PWD-1KG", "INV-D107-W17", "CN7311"). If the source gives no identifier, use
   "<normalized_name>" in lower snake case.
4. name is the canonical name; source_label is the label exactly as it appears in the text.
5. Use only the entity types, attributes and relationships in the catalogue, and only the allowed
   (subject_type, relationship, object_type) pairs. Attribute keys are snake_case as listed.
6. Dates as ISO YYYY-MM-DD. Statuses in lower snake case (e.g. "partially_approved", "rejected").
7. A distributor that submits or receives a claim, credit note or settlement is a Customer whose
   entity_id is the distributor code (e.g. "Distributor D107" -> Customer "D107").
8. Every relationship endpoint must also appear in entities.
9. confidence: your confidence (0-1) that the item is stated exactly as extracted.
"""


def catalogue(onto: Ontology, slice_name: str) -> str:
    sl = onto.slices.slices[slice_name]
    lines = [f"Catalogue for slice '{slice_name}': {sl.description}", "", "Entity types:"]
    for cls in sl.classes:
        c = onto.classes[cls]
        attrs = []
        for k, a in c.attributes.items():
            t = f"{a.type}{'[' + '|'.join(a.values) + ']' if a.values else ''}"
            attrs.append(f"{k} ({t}{', required' if a.required else ''})")
        lines.append(f"- {cls}: {c.description.strip()}")
        if attrs:
            lines.append(f"    attributes: {'; '.join(attrs)}")
    lines += ["", "Allowed relationships (subject -[REL]-> object):"]
    keep = set(sl.classes)
    for rel in sl.relationships:
        for p in onto.relationships[rel].pairs:
            if p.from_ in keep and p.to in keep:
                lines.append(f"- ({p.from_})-[{rel}]->({p.to})")
    return "\n".join(lines)


def build(onto: Ontology, slice_name: str, chunk_text: str) -> tuple[str, str]:
    """(system instruction, user content)."""
    system = RULES + "\n" + catalogue(onto, slice_name)
    user = f"Extract from this document:\n\n<document>\n{chunk_text}\n</document>"
    return system, user
