"""Route a chunk to one ontology slice by keyword score (DECISIONS D40). Ties go to claims_settlement."""
from __future__ import annotations

from codegen.loader import Ontology
from extract.chunk import Chunk

TIE_BREAK = ["claims_settlement", "trade_promotion", "order_to_cash"]


def route(chunk: Chunk, onto: Ontology) -> str:
    text = chunk.text.lower()
    scores = {name: sum(text.count(k.lower()) for k in sl.route_keywords) for name, sl in onto.slices.slices.items()}
    best = max(scores.values())
    for name in TIE_BREAK:
        if scores.get(name) == best:
            return name
    return max(scores, key=scores.get)
