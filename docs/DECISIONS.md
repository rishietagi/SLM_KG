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

## Phase 2 — Finance overlay and MVP extraction (2026-10-04)

Owner decisions for Phase 2:
- Full §13 scope.
- Hybrid ingestion: tabular feeds go through deterministic mappers; narrative documents go through the LLM.
- The LLM is Gemini. The key is read from `GEMINI_API_KEY` and never written to files; `.env` is gitignored.
- The L3 catalogue is drafted by Claude ("make your own"); there is no xlsx.
- The extracted lane enforces only the spec §4 core.

**D37 — New module `ontology/mvp_commercial.yaml`** for the §9 commercial thread.
- **Classes:**
  - PackPricePoint (L3)
  - DemandForecast (L2, consistent with finance Forecast)
  - InventoryPosition (L5)
  - AvailabilityObservation (L5)
  - SellOutTransaction (L5)
  - PurchaseEvent (L6)
- **Pairs:** taken from §5.4 Stages 6–10 and the §9 priority list, e.g. SERVES, STOCKS, FORECASTS, UPLIFTS, OBSERVED_AT, OCCURS_AT, MOTIVATED_BY, INCURRED_FOR, plus additions to LOCATED_IN, BELONGS_TO, MEASURED_FOR, HELD_AT, REFERENCES, CONTAINS, HAS, ISSUED_TO and CONTESTS.
- **No new classes for:** MicroMarket (it is `Geography` with `geography_level=micro_market`, since the spec's Geography definition includes micro-market) and CustomerOrder (it is `SalesOrder`, D19).
- **Distributor loading** is measured on primary `InvoiceLine` quantities, so no order-line class is needed (D36 #7, for the MVP).

**D38 — `Customer ACCOUNT_OF Distributor|Retailer`.** Resolves D18. Claims stay `SUBMITTED_BY Customer` (spec §8). The trade partner is reached through the account. Distributor, Retailer, Outlet, ConsumerSegment and NeedState were promoted from stubs and given attributes.

**D39 — Follow-ups from the Phase-2 ontology review.**
- InventoryPosition is channel stock (quantity only), as distinct from own-book InventoryBalance. Its pair is `HELD_AT Distributor`, where §5.4 says `HELD_AT Location`.
- SellOutTransaction is third-party secondary sales, not Revenue. It is a weekly outlet×SKU aggregate; the spec name is kept.
- PackPricePoint is described as distinct from `SKU.pack_size` and from ListPrice.
- Forecast and DemandForecast cross-reference each other.
- `InvoiceLine.unit` added. CQ6 compares uplift ratios within each side (primary vs baseline, sell-out vs baseline), so the units can differ between primary and secondary.
- Pairs added: `CreditNote ISSUED_TO Customer` and `Dispute CONTESTS PromotionClaim`.
- SERVES and ACCOUNT_OF can carry `valid_from`/`valid_to` from edge_base. The synthetic masters are static.

**D40 — Extraction slices and the LLM schema.**
- `ontology/slices.yaml` defines `trade_promotion`, `claims_settlement` and `order_to_cash`. Routing scores chunks by keywords; the highest score wins and ties go to claims.
- Codegen emits `gen/json_schema/slices/<slice>.json` in the JSON-Schema subset that structured-output APIs accept: no `additionalProperties`, attributes as `[{key, value}]`, and a per-item `confidence`.
- The pipeline coerces values to ontology types and adds provenance from the chunk (file/section). The result is the full spec §7 envelope (`gen/json_schema/extraction_output.json`).
- Outlets, SERVES, account masters, sell-out, availability, inventory and forecasts come from the structured lane.
- Sending synthetic documents to Gemini is approved. Real client documents are not.

**D41 — Drafted finance overlay (curated, `reference/finance/`).**
- 9 of the 16 FinanceDomains (spec names), 15 ProcessGroups and 20 L3ProcessEndpoints, each with one TriggerEvent and one ProcessOutput.
- 28 `ENABLED_BY` edges from activities in Stages 4–9.
- Everything except the domain names is `drafted_beyond_source`.
- Endpoints realising the five processes PROJECT_CONTEXT §6 names (trade promotion accrual, claim settlement, product costing, inventory provisioning, profitability) carry a review note.
- The other 7 domains (strategy & performance, treasury, tax, capex & fixed assets, reporting & analytics, risk & controls, data governance) wait for L3 detail. Without process groups linked to activities they would be orphans.

**D42 — KPIs reach the spine through value outcomes.** 11 KPIs, named from the design notes' Layer 5 list, with drafted definitions and formulas, attach to 8 ValueOutcomes via `MEASURED_BY`. Activities `CREATES` those outcomes.

**D43 — Finance classes given attributes when the MVP needs them.**
- Margin gets `value`, `unit` and `period`.
- New pair `TradeSpend INCURRED_FOR SKU`, for SKU-level listing and visibility spend. This feeds the planted CQ9 pattern.

**D44 — Validation of the extracted lane comes in two stages.**
- **Per staged record:** declared class, relationship and pair; id, name and provenance; attribute types. Failures go to `staging/rejected/` with reasons.
- **Missing spec-"required" attributes are warnings only**, as the owner chose.
- **The spec §4 core constraints run on the resolved, merged entity** (`validate/staging_checks.check_core`, called from the resolver). One fact is often spread over several documents: the claim letter states the amount, and the credit note states the approval and settlement.
- **Core attributes:** claim amount and status; promotion start and end dates; KPI definition, formula and unit; and so on.
- **Core edges:** a claim needs SUBMITTED_BY Customer and CLAIMED_AGAINST TradePromotion; a promotion needs a target.
- **Currency** is required whenever an amount is present.

**D45 — Anchor rules.** `reference/rules/anchor_rules.yaml` links every instance of Brand, Category, SKU, Customer, Distributor, Retailer, Outlet, Channel, ConsumerSegment and NeedState to a curated activity, through ACTS_ON, INVOLVES or TOUCHES. Every other extracted class reaches the spine through its own edges, so the extracted orphan rate is 0 (target < 5%). Anchor edges are lane `extracted`, `source_system: anchor_rules`.

**D46 — Resolution policy.**
- **Order:** exact id → alias table plus master names → fuzzy match (stdlib difflib, ≥ 0.92) → review queue. Always within one class, so do-not-merge pairs can't merge.
- **Masters:** the 18 master/transaction classes must match a structured-lane record. Otherwise the record goes to `staging/review/`, along with its edges.
- **New facts:** documents may introduce claims, credit notes, evidence and disputes.
- **Merging:** the structured lane wins attribute conflicts. Other names go into `aliases`.
- **Status conflicts:** where sources of the same priority disagree, the furthest-progressed status wins (settled > approved/rejected > submitted).

**D47 — The viewer keeps high-volume instance classes out of the initial graph.** Those are SellOutTransaction, AvailabilityObservation, PurchaseEvent, InvoiceLine, InventoryPosition, DemandForecast, SalesOrder, SalesInvoice and Margin. `/api/expand/{id}` adds up to 30 neighbours per relationship on demand. Extracted instances sit in a band below the value chain, and the finance overlay sits under its enabling activities.

**D48 — The synthetic dataset** (`data/synthetic/generate.py`, seed 42) uses the fictional "Aurora Consumer Goods".
- **Masters:** 2 brands (one spanning two categories), 3 categories, 30 SKUs, 3 micro-markets, 3 channels.
- **Partners and outlets:** 10 distributors, 2 retailers, 200 outlets.
- **Promotions:** 6, over FY26 Q1–Q2. They exist both as a TPM export (header, targets, SKUs) and as circulars (mechanic, budget, eligibility), resolved by promotion id.
- **Generated outputs** (CSV, documents, `truth.json`) are gitignored and rebuilt by `make synth`.
- **CQ6 definitions:**
  - The window is the promotion period; the baseline is the equal-length period immediately before it.
  - "Loaded" means primary InvoiceLine quantity up ≥ 30% for the targeted distributor accounts.
  - "No sell-through" means sell-out at the outlets those distributors SERVE is up ≤ 10%. Both thresholds live in `tests/competency/expected.yaml`.
  - Only promotions targeting distributor accounts are evaluated.
  - **Result:** TP2026-003 (+78% primary, −5% sell-out) is the only promotion flagged.

**D49 — LLM runs.**
- Default model `gemini-flash-latest`, overridable with `KG_LLM_MODEL`.
- Temperature 0, with schema-forced JSON (`response_json_schema`).
- Each live call records a fixture in `tests/fixtures/llm/`. These are synthetic-document responses and safe to commit.
- `make test` always uses replay.
- CQ7 is skipped until fixtures exist.

## Scope change — CPG intelligence layer (2026-10-05)

**D50 — The graph is a CPG sector intelligence layer, not an instance graph.**
*Owner direction:* CPG broadly (not only FMCG); value chain, L1/L2/L3 processes, product and asset, ecosystem and channel, performance and risk, consumer and experience; **no data about clients, companies, people or transactions**.
- **Removed from the working tree** (kept in git history, commit `d593136`):
  - the synthetic dataset;
  - tabular staging, LLM extraction and resolution;
  - `ontology/mvp_commercial.yaml` and `ontology/slices.yaml`;
  - instance CQ6/CQ7;
  - staging metrics;
  - the viewer's heavy-class and expand code;
  - `.env`. **The Gemini key pasted in chat should be revoked.**
- **Superseded:** D37–D40 and D43–D49.
- **D41/D42** (drafted finance L3 overlay, KPIs) carry forward. FinanceDomain nodes are dropped: ProcessArea is now the parent of ProcessGroup in the graph. The FinanceDomain CONTAINS ProcessGroup pair stays in finance.yaml as spec schema only.
- **New module `ontology/intelligence_layers.yaml`:**
  - ProcessArea (L2, the L1 process level);
  - ProductAssetConcept (L3);
  - EcosystemConcept (L4, with `concept_kind` participant / channel / geography);
  - RiskType (L5);
  - ConsumerConcept (L6);
  - about 30 concept relationships taken from PROJECT_CONTEXT §5.4.
- **Hooks retargeted to the concept classes:**
  - ACTS_ON → ProductAssetConcept;
  - INVOLVES → EcosystemConcept;
  - TOUCHES → ConsumerConcept;
  - RiskType AFFECTS Activity.
  The old instance stub classes (Formulation, Batch, Plant, Distributor, Outlet, …) are now concept nodes.
- **finance.yaml stays** as the finance spec schema. It is unpopulated except for ProcessGroup, L3ProcessEndpoint, TriggerEvent, ProcessOutput and KPI, whose descriptions are now generic.

**D51 — Layer 2 hierarchy (light depth, owner choice).**
- 14 ProcessAreas, named in PROJECT_CONTEXT §2 (source-backed).
- 26 ProcessGroups: the 15 finance groups regrouped plus 11 new.
- 40 L3 processes: 20 finance plus 20 new, each with one trigger and one output.
- 64 ENABLED_BY edges.
- New groups, new L3s, and the area→group placement are drafted. **For owner review:** `pp_pricing` under Order-to-cash and `cf_distributor_performance` under Data-to-insight are arguable.

**D52 — Layers 3–6 concepts.**
- **Names** come from the design notes' six-layer lists, so they are source-backed:
  - 19 product and asset concepts;
  - 18 ecosystem concepts ("Modern trade" is a channel, not a chain);
  - 23 KPIs (the 11 existing plus 12 from the Layer 5 list) with 14 value outcomes;
  - 6 risk types (3 source-backed, 3 drafted);
  - 18 consumer concepts.
- **Hook links from activities are drafted.**
- **Concept relationships** cite §5.4/§6.1 where stated; the rest are drafted.
- **Edge cleanup:** Formulation→Ingredient is CONTAINS only (the duplicate REQUIRES was removed). Recipe is described as the food and beverage form of a formulation.
- **THREATENS (RiskType→concept) is kept separate from AFFECTS** (RiskType→activity, the Layer-5 hook). AFFECTS is reserved for the hook, so hook coverage can be measured.
- **No new sub-sectors** (owner choice). Food & beverage, personal care and home care remain.

**D53 — `RELATES_TO_BATCH` is renamed `TRACES_TO_BATCH`.** The old name used the forbidden `RELATES_TO` stem (CLAUDE.md rule 4).
- **Do-not-merge pairs at concept level:** Brand, Product family, Category and SKU are rows of one concept class. They are curated rows and never pass through entity resolution, so rule 11 can't be violated by merging. If resolution returns, enforce the pairs by row id.

**D54 — Competency questions 5–10 are concept-level** (PROJECT_CONTEXT §12 updated).
- CQ5: L3 processes enabling outlet execution.
- CQ6: outlet KPIs and risks.
- CQ7: manufacturing product and asset subgraph.
- CQ8: ecosystem participants and channels from Stage 7 to 10.
- CQ9: Stage-10 consumer concepts, and complaint → batch → plant.
- CQ10: trade-promotion-management processes across stages.
All ten pass (`tests/competency/`).

**D55 — Viewer as a concept explorer.**
- **Layouts:** Layered (spine on top, one band per layer; each concept sits under the mean column of the activities it links to), Rings (concentric by layer), and Force.
- **Filters:** layer chips, with type and relationship chips under Advanced; hook edges are hidden in the overview and shown on focus.
- **Activity 360°:** the panel groups neighbours by layer.
- **CQ1–10 cards.**
- **Report:** nodes per layer and hook coverage, which `make report` also prints.
- ValueOutcome (an L1 class) is drawn in the L5 band next to its KPIs.

