"""Staging records in the finance spec §7 envelope shape, one JSONL file per source.

Each line is {"kind": "entity" | "relationship" | "unresolved", ...}. Entities and relationships carry
canonical names, `<Class>:<code>` ids and a `source` provenance block.
"""
from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from pathlib import Path

from codegen.loader import ROOT

STAGING = ROOT / "staging"
EXTRACTED = STAGING / "extracted"
REJECTED = STAGING / "rejected"
UNRESOLVED = STAGING / "unresolved"
REVIEW = STAGING / "review"
RESOLVED = STAGING / "resolved"


def nid(cls: str, code: object) -> str:
    code = str(code).strip()
    return code if code.startswith(f"{cls}:") else f"{cls}:{code}"


def source(system: str, record_id: str, reference: str, confidence: float = 1.0) -> dict:
    return {"source_system": system, "source_record_id": str(record_id), "source_reference": reference,
            "extraction_confidence": confidence}


def entity(cls: str, code: object, name: str, src: dict, source_label: str | None = None,
           description: str | None = None, **attributes) -> dict:
    return {"kind": "entity", "entity_type": cls, "entity_id": nid(cls, code), "name": str(name),
            "source_label": source_label or str(name), "description": description,
            "attributes": {k: v for k, v in attributes.items() if v is not None and v == v and v != ""},
            "source": src}


def rel(subject_type: str, subject_code: object, relationship: str, object_type: str, object_code: object,
        src: dict, **attributes) -> dict:
    return {"kind": "relationship", "subject_type": subject_type, "subject_id": nid(subject_type, subject_code),
            "relationship": relationship, "object_type": object_type, "object_id": nid(object_type, object_code),
            "attributes": {k: v for k, v in attributes.items() if v is not None}, "source": src}


def unresolved(source_text: str, reason: str, src: dict, candidate_entity_types: list[str] | None = None,
               candidate_relationships: list[str] | None = None) -> dict:
    return {"kind": "unresolved", "source_text": source_text, "reason": reason,
            "candidate_entity_types": candidate_entity_types or [],
            "candidate_relationships": candidate_relationships or [], "source": src}


def write_jsonl(path: Path, records: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, default=str, ensure_ascii=False) + "\n")
            n += 1
    return n


def read_jsonl(path: Path) -> Iterator[dict]:
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def read_dir(directory: Path) -> Iterator[tuple[str, dict]]:
    for path in sorted(directory.glob("*.jsonl")):
        for r in read_jsonl(path):
            yield path.name, r
