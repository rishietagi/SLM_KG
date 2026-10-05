# CLAUDE.md — CPG Intelligence Graph

## What this project is
A single, layered knowledge graph for the CPG sector that grounds a Consumer Markets SLM. It is a sector **intelligence layer**: concepts, processes and relationships only, with no transactional or party data (DECISIONS D50). The CPG value chain (11 stages) is the spine; five outer layers (processes, product/asset, ecosystem/channel, performance/risk, consumer/experience) enrich the same nodes through declared hook relationships.

Full design: `docs/PROJECT_CONTEXT.md`. Read it at the start of any new phase or before changing the ontology.
Decision log: `docs/DECISIONS.md`. Append every design decision with date and reason.

## Current phase
Phase 2 — Six-layer intelligence graph and viewer: exit criteria green on 2026-10-05 (owner review of drafted rows pending). Next: Phase 3 — Retrieval and SLM training pairs. (Update this line when a phase's exit criteria pass.)
Environment: conda env `mmsa` (`C:/miniconda/envs/mmsa/python.exe`, make in `Library/bin`), kuzu 0.11.3 active backend — see DECISIONS D1.

## Stack
- Python 3.12, managed with `uv`
- Graph engine: LadybugDB (`real_ladybug`), behind `graph/store.py::GraphStore`. Fallback: Kuzu 0.11.3 pinned.
- Pydantic v2, PyYAML, pandas + pyarrow (parquet), pytest
- LLM extraction via `extract/llm_client.py` (pluggable endpoint, schema-forced output)

## Commands
- `make gen` — regenerate DDL, Pydantic models, JSON schemas from `ontology/`
- `make validate` — ontology integrity + reference data + staging checks
- `make load` — rebuild the graph database from parquet
- `make test` — unit + competency tests
- `make report` — quality metrics (orphans, edges per node, unresolved items)

Run `make validate && make test` before declaring any task done.

## Hard rules
1. `ontology/*.yaml` is the single source of truth. Never hand-edit anything in `gen/`; change the YAML and run `make gen`.
2. Never reference a class or relationship that is not declared in the ontology. If one is needed, add it to the YAML first and log it in `docs/DECISIONS.md`.
3. Naming: node labels PascalCase, relationship types UPPER_SNAKE_CASE, properties snake_case. Finance spec names are converted via `ontology/rel_name_map.yaml`.
4. No generic relationships (`RELATES_TO`, `LINKED_TO`) when a specific one fits.
5. Every node and edge carries provenance: `source_system`, `source_record_id`, `source_reference`, `extraction_confidence`, `lane` (`curated` | `extracted`).
6. Two lanes, never mixed: curated reference data lives in `reference/` and is human-reviewed. The extracted lane (`staging/` → validate → resolve → load) is deferred; no instance data is in scope (D50).
7. Extraction is explicit-only: no inferred entities, no calculated or rescaled amounts. Ambiguity goes to `unresolved_items`, not into the graph.
8. Every outer-layer node must have a path to a `ValueChainActivity`. Orphans fail validation.
9. Only `graph/backends/*` imports the graph engine. Everything else uses `GraphStore`.
10. Bulk loads use parquet + `COPY FROM`, never row-by-row inserts.
11. Never auto-merge the "do not merge" pairs (Customer/Consumer, Brand/ProductFamily, Channel/Customer, Budget/Forecast, Claim/Deduction, Risk/Issue, Control/Process, CostCentre/ProfitCentre, TradePromotion/Discount, Category/SKU).
12. Brand and Category are independent hierarchies; never model Category as belonging to Brand.

## Data handling
- The graph holds sector knowledge only; do not add client, company, person or transaction data.
- Do not send real client documents to an external model API unless `docs/DECISIONS.md` records that it is approved.
- Never commit real client data. `docs/source/` holds specs only.

## Working style
- Start each phase in plan mode; present the plan and wait for approval before editing files.
- Work in small, testable steps; keep the Makefile targets working after every step.
- Use the `ontology-reviewer` subagent before merging any ontology change, and the `cypher-tester` subagent for competency tests.
- Use the `kg-extraction` skill for anything touching extraction prompts or schemas (deferred while the extracted lane is out of scope).
- When a spec item is marked *confirm* in `docs/PROJECT_CONTEXT.md` §6.1, ask the owner instead of deciding.
- Keep explanations short; show diffs, test output and metrics rather than describing them.
