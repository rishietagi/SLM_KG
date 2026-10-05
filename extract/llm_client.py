"""Pluggable LLM client with schema-forced output (PROJECT_CONTEXT §10.2 step 3).

KG_LLM selects the backend:
  replay (default) — recorded responses in tests/fixtures/llm/<key>.json; offline and deterministic.
  gemini           — Google Gemini via google-genai with response_json_schema; records a fixture per call.
GEMINI_API_KEY is read from the environment or a gitignored .env file; it is never written anywhere.
KG_LLM_MODEL overrides the Gemini model.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Protocol

from codegen.loader import ROOT

FIXTURES = ROOT / "tests" / "fixtures" / "llm"
DEFAULT_GEMINI_MODEL = "gemini-flash-latest"


class MissingFixture(RuntimeError):
    pass


class LLMClient(Protocol):
    name: str

    def extract(self, system: str, user: str, schema: dict) -> dict: ...


def fixture_key(system: str, user: str, schema: dict) -> str:
    blob = json.dumps([system, user, schema], sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:20]


def _load_dotenv() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


class ReplayClient:
    name = "replay"

    def extract(self, system: str, user: str, schema: dict) -> dict:
        path = FIXTURES / f"{fixture_key(system, user, schema)}.json"
        if not path.exists():
            raise MissingFixture(f"no recorded response {path.name}; run `KG_LLM=gemini make extract` to record")
        return json.loads(path.read_text(encoding="utf-8"))["response"]


class GeminiClient:
    def __init__(self, model: str | None = None, record: bool = True) -> None:
        _load_dotenv()
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is not set (environment or .env)")
        from google import genai  # imported lazily so replay needs no SDK

        self._genai = genai
        self._client = genai.Client(api_key=key)
        self.model = model or os.environ.get("KG_LLM_MODEL") or DEFAULT_GEMINI_MODEL
        self.name = f"gemini:{self.model}"
        self.record = record

    def extract(self, system: str, user: str, schema: dict) -> dict:
        from google.genai import types

        resp = self._client.models.generate_content(
            model=self.model,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system, temperature=0, response_mime_type="application/json",
                response_json_schema=schema),
        )
        data = json.loads(resp.text)
        if self.record:
            FIXTURES.mkdir(parents=True, exist_ok=True)
            key = fixture_key(system, user, schema)
            (FIXTURES / f"{key}.json").write_text(
                json.dumps({"key": key, "model": self.model, "response": data}, indent=2, ensure_ascii=False),
                encoding="utf-8")
        return data


def get_client() -> LLMClient:
    backend = os.environ.get("KG_LLM", "replay").lower()
    if backend == "replay":
        return ReplayClient()
    if backend == "gemini":
        return GeminiClient()
    raise ValueError(f"unknown KG_LLM backend {backend!r}")
