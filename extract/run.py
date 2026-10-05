"""`make extract`: documents -> chunk -> route -> LLM (schema-forced) -> staging/extracted/llm_<doc>.jsonl.

Offline by default (KG_LLM=replay). `KG_LLM=gemini make extract` calls Gemini and records fixtures.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date, datetime

from codegen.loader import ROOT, Ontology, load_ontology
from codegen.meta import Attribute
from extract.chunk import Chunk, chunk_document
from extract.llm_client import LLMClient, MissingFixture, get_client
from extract.prompts import build
from extract.route import route
from pipeline.staging import EXTRACTED, entity, nid, rel, source, unresolved, write_jsonl

DOCS = ROOT / "data" / "synthetic" / "documents"
SCHEMAS = ROOT / "gen" / "json_schema" / "slices"
DATE_FORMATS = ("%Y-%m-%d", "%d %B %Y", "%d %b %Y", "%d-%m-%Y", "%d/%m/%Y")


def _snake(k: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", k.strip().lower()).strip("_")


def coerce(attrs: dict[str, Attribute], pairs: list[dict]) -> tuple[dict, list[str]]:
    """[{key, value}] -> typed attribute dict. Returns (attributes, problems)."""
    out: dict = {}
    problems: list[str] = []
    for kv in pairs:
        key, raw = _snake(kv.get("key", "")), str(kv.get("value", "")).strip()
        if not key or raw == "":
            continue
        if key.endswith("_text") and attrs.get(key[:-5]) and attrs[key[:-5]].type == "decimal":
            out[key] = raw
            continue
        a = attrs.get(key)
        if a is None:
            problems.append(f"attribute {key!r} not in ontology (value {raw!r})")
            continue
        try:
            out[key] = _convert(a, raw)
        except ValueError:
            problems.append(f"attribute {key}={raw!r} is not a valid {a.type}")
            if a.type == "decimal":
                out[f"{key}_text"] = raw
        if a.type == "decimal":
            out.setdefault(f"{key}_text", raw)
    return out, problems


def _convert(a: Attribute, raw: str):
    t = a.type
    if t == "decimal" or t == "double":
        num = re.sub(r"[^0-9.\-]", "", raw.replace(",", ""))
        if not num or num in ("-", "."):
            raise ValueError
        return float(num)
    if t == "int64":
        return int(float(raw.replace(",", "")))
    if t == "bool":
        if raw.lower() in ("true", "yes", "y", "1"):
            return True
        if raw.lower() in ("false", "no", "n", "0"):
            return False
        raise ValueError
    if t == "date":
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(raw, fmt).date().isoformat()
            except ValueError:
                pass
        raise ValueError
    if t == "enum":
        v = _snake(raw)
        if v not in (a.values or []):
            raise ValueError
        return v
    if t == "string_list":
        return [x.strip() for x in raw.split(",") if x.strip()]
    return raw


def to_records(onto: Ontology, chunk: Chunk, resp: dict, client: LLMClient) -> list[dict]:
    pairs = onto.pair_set()
    system = f"llm_{client.name}"
    recs: list[dict] = []
    for e in resp.get("entities", []):
        cls = e["entity_type"]
        src = source(system, chunk.record_id, chunk.reference, float(e.get("confidence", 0.0)))
        attrs, problems = coerce(onto.classes[cls].attributes, e.get("attributes", []))
        recs.append(entity(cls, e["entity_id"], e.get("name") or e["entity_id"], src,
                           source_label=e.get("source_label"), **attrs))
        recs += [unresolved(f"{cls} {e['entity_id']}: {p}", "attribute could not be mapped", src, [cls]) for p in problems]
    for r in resp.get("relationships", []):
        src = source(system, chunk.record_id, chunk.reference, float(r.get("confidence", 0.0)))
        key = (r["relationship"], r["subject_type"], r["object_type"])
        if key not in pairs:
            recs.append(unresolved(f"({r['subject_type']} {r['subject_id']})-[{r['relationship']}]->"
                                   f"({r['object_type']} {r['object_id']})", "relationship pair not allowed by ontology",
                                   src, [r["subject_type"], r["object_type"]], [r["relationship"]]))
            continue
        recs.append(rel(r["subject_type"], r["subject_id"], r["relationship"], r["object_type"], r["object_id"], src))
    for u in resp.get("unresolved_items", []):
        src = source(system, chunk.record_id, chunk.reference, 0.0)
        recs.append(unresolved(u["source_text"], u["reason"], src, u.get("candidate_entity_types")))
    return recs


def run() -> int:
    onto = load_ontology()
    client = get_client()
    if not DOCS.exists():
        raise SystemExit("no documents: run `make synth` first")
    for old in EXTRACTED.glob("llm_*.jsonl"):
        old.unlink()
    stats: Counter = Counter()
    routes: Counter = Counter()
    for doc in sorted(DOCS.glob("*.md")):
        recs: list[dict] = []
        for chunk in chunk_document(doc):
            sl = route(chunk, onto)
            routes[sl] += 1
            system, user = build(onto, sl, chunk.text)
            schema = json.loads((SCHEMAS / f"{sl}.json").read_text(encoding="utf-8"))
            try:
                resp = client.extract(system, user, schema)
            except MissingFixture as e:
                stats["missing_fixtures"] += 1
                print(f"extract: {doc.name}: {e}")
                continue
            stats["chunks"] += 1
            recs += to_records(onto, chunk, resp, client)
        write_jsonl(EXTRACTED / f"llm_{doc.stem}.jsonl", recs)
        stats.update(r["kind"] for r in recs)
    print(f"extract [{client.name}]: {stats['chunks']} chunks ({dict(routes)}), {stats['entity']} entities, "
          f"{stats['relationship']} relationships, {stats['unresolved']} unresolved, "
          f"{stats['missing_fixtures']} missing fixtures")
    return 1 if stats["missing_fixtures"] else 0


__all__ = ["run", "coerce", "to_records", "nid", "date"]
