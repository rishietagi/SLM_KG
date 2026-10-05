"""Split markdown documents into chunks with file/section provenance (PROJECT_CONTEXT §10.2 step 1)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from codegen.loader import ROOT

MAX_CHARS = 6000  # documents shorter than this stay whole so headings keep their context


@dataclass(frozen=True)
class Chunk:
    file: str  # repo-relative path
    index: int
    section: str
    text: str

    @property
    def reference(self) -> str:
        return f"{self.file}#{self.section}"

    @property
    def record_id(self) -> str:
        return f"{Path(self.file).stem}#{self.index}"


def chunk_document(path: Path) -> list[Chunk]:
    text = path.read_text(encoding="utf-8")
    rel = path.resolve().relative_to(ROOT).as_posix()
    title = next((ln[2:].strip() for ln in text.splitlines() if ln.startswith("# ")), path.stem)
    if len(text) <= MAX_CHARS:
        return [Chunk(rel, 0, _slug(title), text)]
    parts = re.split(r"(?m)^## ", text)
    head, sections = parts[0], parts[1:]
    chunks = []
    for i, sec in enumerate(sections):
        name = sec.splitlines()[0].strip()
        chunks.append(Chunk(rel, i, _slug(f"{title} / {name}"), f"{head.strip()}\n\n## {sec}"))
    return chunks or [Chunk(rel, 0, _slug(title), text)]


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
