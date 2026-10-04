# Decision log

Append-only. Each entry: date, decision, reason. Plan question IDs (N1–N9, C1–C4, Q-ENV) refer to the
approved Phase-1 plan; the owner approved all proposed defaults on 2026-10-04.

## Phase 1 — Foundation and value-chain spine (2026-10-04)

### Environment and repository

**D1 — Run in conda env `mmsa`; kuzu is the active backend.** (Q-ENV)
`mmsa` is the only existing env with kuzu. It provides Python 3.11.16 and kuzu 0.11.3, the pinned fallback version. `pyarrow` was pip-installed and `make` conda-installed (`Library/bin/make.exe`). `real_ladybug` is not installed, so `graph/backends/ladybug.py` is written but unexercised. `KG_BACKEND` selects the backend (default `kuzu`). `pyproject.toml` declares `requires-python >=3.11` rather than 3.12 and keeps uv metadata for later. *Reason:* the owner asked to use an existing env with kuzu.

**D2 — Docs moved and git initialised.** `PROJECT_CONTEXT.md` moved to `docs/` and both specs to `docs/source/`, matching §14. `git init` was run, with no commits made.

**D3 — Additions to the §14 repo structure.**
- `codegen/`: ontology meta-model, loader and generators.
- `pipeline/`: CLI behind every make target, curated loader, report.
- `viewer/`: graph and schema UI.
- `ontology/common.yaml`: type map, shared node/edge attributes, forbidden relationships, do-not-merge pairs.
- `.claude/hooks/`: hook script.

*Reason:* §14 has no home for codegen or shared ontology definitions.

**D4 — Makefile targets are thin wrappers over `python -m pipeline.cli <target>`.** `PYTHON` defaults to the mmsa interpreter. *Reason:* everything also works without make on Windows.

### Ontology format

**D5 — The YAML schema is defined as Pydantic models in `codegen/meta.py`.**
- Classes: `layer` (1–6, required), `description`, `source_key`, `spec_ref`, `stub`, `attributes{type, required, values, description}`.
- Relationships: `description`, `hook_layer`, `pairs[{from, to, cardinality, note}]`, `properties`.
- The loader merges a relationship name used in several modules into one rel table. Pairs must be unique and shared properties must agree.
- Modules load spine first (`layer1_value_chain`, `hooks`, then the rest), so spine descriptions win.

**D6 — Every node table's PK is `id STRING`.** The spec's key name (e.g. `claimID`) is kept as `source_key`. Curated IDs are `<Class>:<slug>`, so an id alone resolves its table (PROJECT_CONTEXT §4).

**D7 — Provenance and retrieval attributes are injected from `common.yaml`.**
- `node_base` (16 attributes) holds `id`, `name`, `description`, `aliases`, `source_label`, the provenance fields (§3.5), `lane`, `reviewed`, `drafted_beyond_source`, `review_note`, `valid_from`, `valid_to` and `last_updated`.
- `edge_base` holds the provenance fields plus `amount`, `currency`, `valid_from` and `valid_to` (finance spec §7 relationship attributes).
- `drafted_beyond_source` and `review_note` are additions, so curated rows not stated in a source can be flagged for review.

**D8 — Type map.** Mappings: `string` STRING, `int64` INT64, `double` DOUBLE, `bool` BOOLEAN, `date` DATE, `timestamp` TIMESTAMP, `string_list` STRING[]. Enums are stored as STRING and checked by Pydantic and validators.

**D9 — `decimal` maps to DOUBLE plus a companion `<attr>_text STRING`.** kuzu 0.11.3 parquet COPY fails on DECIMAL ("Unsupported converted type", tested 2026-10-04). The `_text` column keeps the amount exactly as stated (finance spec §1.3–1.4); the DOUBLE is for querying. Revisit if Ladybug supports DECIMAL in parquet COPY.

### Finance conversion (PROJECT_CONTEXT §6, finance spec §2–3)

**D10 — `finance.yaml` and `rel_name_map.yaml` were generated once from the spec, then maintained by hand.**
- A one-off parser (not kept in the repo) read the spec's class blocks and `(A)-[:rel]->(B)` lines.
- Mechanical camelCase→UPPER_SNAKE gives 205 spec classes, 209 declared in finance.yaml (with additions), and 267 original triples. That becomes 313 map entries once generic `Entity` is expanded.
- Every original triple is in `rel_name_map.yaml` with an action: converted, renamed, mapped, retargeted, deferred or dropped.
- `make validate` checks traceability in both directions.

**D11 — §6.1 resolutions applied.**

| Item | Resolution |
|---|---|
| FiscalPeriod, Currency, Provision (`provision_type`), Reconciliation (`reconciliation_type`), Approval, Resolution, IntercompanyTransaction | declared (layer 2) |
| Claim | mapped to PromotionClaim |
| CostVariance | Variance with `variance_type = cost` |
| CostAllocation ASSIGNS Cost | dropped; AllocationRule ALLOCATES CostPool / ASSIGNS_TO CostCentre\|ProfitCentre covers it (**C1, confirmed default**) |
| Sample, Retest, Mapping | deferred; their 3 relationships omitted |
| Auditor | Organization with `organization_type = auditor`, so Finding RAISED_BY Organization (**C2**) |
| Report | ManagementReport |
| FinancialFact | ActualResult, so Analysis USES ActualResult (**C3**) |
| CarryingValue | property `carrying_value` on FixedAsset (see D20) |
| CashGLBalance | Balance |
| DecisionOption | declared in Layer 1 |
| BusinessFact | SourceEvidence for the curated lane: Decision BASED_ON SourceEvidence; ActualResult to be added as a second pair in Phase 2 (**C4**) |
| JournalLine relatesTo | ATTRIBUTED_TO |
| Category belongsTo Brand | dropped. Replacement: ProductFamily BELONGS_TO_CATEGORY Category, ProductFamily BELONGS_TO_BRAND Brand, Category PARENT_OF Category |

**D12 — Subtypes become type properties.**
- VarianceDriver subtypes become `driver_type` enum: price, volume, mix, fx, material_cost, freight, timing.
- CostComponent subtypes become `component_type` enum: material, packaging, conversion, overhead, freight, warranty, return.
- `PVMAnalysis CONTAINS Price/Volume/MixVariance` becomes `CONTAINS VarianceDriver`.
- PromotionMechanic examples are documented on `mechanic_type`.

**D13 — CONSUMES/PRODUCES use explicit target lists.**
- `ValueChainActivity → Input / Output`.
- `L3ProcessEndpoint CONSUMES|PRODUCES`: ProcessOutput (PRODUCES) plus 24 transaction and document classes (SalesOrder … DepreciationEntry).
- Also `SalesOrder CONSUMES CreditLimit` and `PromotionSettlement CONSUMES PromotionAccrual`.
- Batch/ProductionOrder CONSUMES/PRODUCES from §5.4 are deferred with D27.

**D14 — Promotion relationship names unified with Layer 1.** TradePromotion `offeredTo` Customer → `TARGETS`; TradePromotion `operatesIn` Geography → `VALID_IN`. Customer/Supplier `operatesIn` stays `OPERATES_IN`. (N4)

**D15 — The remaining generic `relatesTo` uses are renamed.** Deduction→SalesInvoice is `TAKEN_AGAINST`; Dispute→Deduction is `CONTESTS`; APException→SupplierInvoice is `RAISED_ON`. (N3)

**D16 — CostCentre and ProfitCentre stay separate tables; `isA ResponsibilityCentre` is dropped.** They are a do-not-merge pair, and JournalLine targets each one separately. Both gain `BELONGS_TO BusinessUnit`. ResponsibilityCentre keeps `centre_type`. (N6)

**D17 — `BusinessUnit BELONGS_TO Organization` is dropped.** It is the redundant inverse of `Organization CONTAINS BusinessUnit`. (N8)

**D18 — Hook targets missing from finance are declared as stubs in `hooks.yaml`.** The stubs are Formulation, Batch, PackagingMaterial, Plant, Warehouse (L3); Distributor, Retailer, Outlet, LogisticsProvider (L4); ConsumerSegment, NeedState, Touchpoint (L6). Distributor is separate from Customer. The spec §8 example still extracts a claim-submitting distributor as Customer; the Distributor↔Customer link is a Phase-2 decision. (N5)

**D19 — Cross-spec duplicates stay as separate classes, with distinguishing descriptions.** The pairs are CustomerOrder (L1, Phase 2) vs SalesOrder, TriggerEvent vs BusinessEvent, ProcessOutput vs Output, and Evidence vs SourceEvidence. In extraction, "customer order" resolves to SalesOrder and "promotion spend" to TradeSpend. (N4)

**D20 — CarryingValue retargets.** `ImpairmentEntry reduces CarryingValue` becomes `ImpairmentEntry IMPAIRS FixedAsset`. `GainLoss derivedFrom CarryingValue` becomes `GainLoss DERIVED_FROM FixedAsset`. (N7)

**D21 — Layer tags.**
- Finance process structure, organization, accounting, transactions, planning, costing, treasury, tax and assets are layer 2.
- Brand, Category, ProductFamily, SKU are layer 3.
- Customer, Supplier, Channel, Geography, Location are layer 4.
- KPI, metrics, results, variances, profitability, margin, trade spend, risk, control, audit and issue are layer 5.
- Role, Organization, ValueDriver are declared once in Layer 1, with the finance attributes merged in (`organization_type`, `driver_type`; `roleName` → `name`).
- KPI stays in finance.

**D22 — Attribute renames.**
- `date` becomes `document_date`.
- L3ProcessEndpoint `trigger`/`output` become `trigger_description`/`output_description`.
- `roleName`/`accountName` become `name`.
- `parentCategory`/`parentGeography` are dropped in favour of the `PARENT_OF`/`PART_OF` edges.

**D23 — do-not-merge pairs use canonical names.** Claim/Deduction becomes PromotionClaim/Deduction; Control/Process becomes Control/L3ProcessEndpoint.

### Spec conflicts (followed PROJECT_CONTEXT)

**D24 — Where the design notes conflict with PROJECT_CONTEXT, PROJECT_CONTEXT wins.**
- No `Dependency` class; DEPENDS_ON is an edge.
- FOLLOWS is not stored.
- DecisionOption and SubSector/VARIES_IN are declared.
- `TradePromotion UPLIFTS` replaces `Promotion UPLIFTS`.
- `RELATES_TO_BATCH` replaces `RELATES_TO`.
- MVP names are `SERVES`, `BELONGS_TO_*` and `TradeSpend`.
- ENABLED_BY goes from ValueChainActivity, not Stage. "Maintain-to-Operate" (design Build 2, absent from the L2 list) is noted for Phase 2.
- Stage names follow the §2 hierarchy; variants are kept in `aliases`.

### Curated Layer-1 data

**D25 — All 103 activities are kept verbatim** (target was 60–80), since consolidating would editorialise the source. (N1)

**D26 — Content not stated in the source is drafted and flagged.** Each such row has `drafted_beyond_source: true` and usually a `review_note`; every row has `reviewed: false`. (N2)
- **Flagged:** the 7 BusinessEvents outside the §2 chain; 3 Inputs; 10 of the 14 Decisions and their options; every TRIGGERED_BY, CONSUMES, PRODUCES, REQUIRES, DEPENDS_ON, BECOMES_INPUT_TO and VARIES_IN edge; and all sub-sector variations. Neither source describes sub-sector differences.
- **Totals at load:** 51 nodes and 339 edges flagged; all 293 nodes await review.
- **Source-backed:** the 11 stages (names, purposes), 103 activities, 75 outputs, 7 Stage-1 inputs, the 15 §2-chain events and the PRECEDES order.

**D27 — The §5.4 per-stage object relationships are deferred to Phase 2+.** That is about 100 edges over about 80 more L3–L6 classes, such as OpportunityArea, BeatPlan and ProductRecall. Phase 1 declares only the hook targets. (N9)

**D28 — Stage fields.** `definition` is summarised from each stage's activity list. `entry_event`/`exit_event` are drafted from the §2 chain. `upstream_stage`/`downstream_stage` are denormalised from PRECEDES, and the validator checks they agree.

**D29 — Added pair: `ValueChainStage SUPPORTED_BY_EVIDENCE SourceEvidence`.** Design notes §2 list "relevant source evidence" per stage. One SourceEvidence node per cited source section.

### Validation, load and engine quirks

**D30 — Orphan rule.** Every node must reach the CPGValueChain root, treating edges as undirected. Any node reaching the root reaches the spine of stages and activities. The rule runs on reference data in `make validate` and on the loaded DB in `make report`.

**D31 — kuzu 0.11.3 workarounds.**
- A `$param` inside a list lambda (`any(x IN l WHERE … $p …)`) crashes with KU_UNREACHABLE; bind it first with `WITH $p AS p`.
- A list lambda over a NULL list returns the previous row's result. The parquet writer therefore stores empty lists instead of NULL for STRING[].
- Untyped node patterns return the union of every table's properties, so queries return explicit fields.

**D32 — Load is a full rebuild.** It deletes `db/cpg.kuzu` (single-file DB), applies `gen/ddl/schema.cypher` (237 node tables, 132 rel tables, 349 FROM–TO pairs), then runs COPY FROM per node table and per rel FROM–TO parquet file. Multi-pair rel tables pass `(from=…, to=…)`.

### Tooling

**D33 — PostToolUse hook.** `.claude/hooks/validate_on_edit.py` runs `make validate` after Edit/Write/MultiEdit on `ontology/` or `reference/`. On failure it exits 2 and returns the output to Claude. An ontology edit makes `gen/` stale, so the hook hints to run `make gen`.

**D34 — Project subagents need a new session.** `.claude/agents/ontology-reviewer.md` and `cypher-tester.md` register only when a session starts. In this session the review ran via a general-purpose agent following `ontology-reviewer.md`.

**D35 — Graph and schema viewer** (owner request; not in §13).
- `viewer/server.py` (FastAPI) opens the DB read-only through GraphStore. Endpoints: `/api/schema`, `/api/graph`, `/api/node/{id}`, `/api/competency/{n}`, `/api/report`, `/docs-src/*` (cited docs only).
- `viewer/static/index.html` uses the Tailwind Play CDN and Cytoscape.js with fcose.
- Run with `make viewer` on port 8000. Stop it before `make load`, because kuzu holds a file lock.
- The CDN build of Tailwind is fine for a local tool. Switch to the Tailwind CLI if the viewer is ever deployed.

**D36 — Ontology review (2026-10-04), first pass.** Verdict: structurally clean. 0 undeclared classes, every class layered, every finance pair traceable.
- **Fixed now:**
  - `hook_layer` is per pair. Finance pairs under AFFECTS and MEASURED_BY no longer count as hooks.
  - The rel_name_map notes for TARGETS/VALID_IN now cite §5.4 Stage 8.
  - The IMPAIRS entry notes the rename.
  - The TARGETS description is corrected.
  - Retailer is distinguished from Customer.
- **New warning:** `make validate` now warns about the 21 finance classes with no relationships in the spec (e.g. TrialBalance, GeneralLedger, Person, TaxRate). Any instance of these would be an orphan. This becomes an error once Phase 2 extracts them.
- **Open for the owner (Phase 2):** these findings are spec-inherited and need a decision rather than a fix.
  1. Edges for, or deferral of, the 21 isolated classes.
  2. Spec "required" attributes vs explicit-only extraction: reject, or relax to optional for the extracted lane?
  3. Regulator vs TaxAuthority (merge, or Organization + type).
  4. ResponsibilityCentre vs CostCentre/ProfitCentre routing; Budget APPROVED_FOR only reaches ResponsibilityCentre.
  5. Inverse-direction duplicates: OWNS/OWNED_BY, PERFORMS/PERFORMED_BY, GOVERNS/GOVERNED_BY, COMPARES/COMPARED_AGAINST, MATCHES/MATCHED_TO, TRACES/TRACES_TO, PART_OF vs PARENT_OF.
  6. Splitting the broad HAS and USES into specific names.
  7. Quantity/price on SalesOrder/PurchaseOrder CONTAINS SKU (or an order-line class).
  8. Layer of FixedAsset/AssetClass/CGU (2 vs 3) and Location (4) vs Plant/Warehouse (3).
  9. Overlaps to document or merge: Revenue/Margin vs ActualResult, Jurisdiction/Geography, Filing/TaxReturn, Exposure/FXExposure, FinancialMetric/MetricDefinition/KPI, Formula vs `KPI.formula`.
  10. Attributes duplicating edges (`owner`, TrialBalance `legal_entity`/`period`) and `effective_from`/`effective_to` vs `valid_from`/`valid_to`.
  11. SUPPORTED_BY means both "participant organisation" (Layer 1, per PROJECT_CONTEXT §5.2) and "evidence" (finance).
