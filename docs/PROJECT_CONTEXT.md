# CPG Intelligence Graph — Project Context

This document is the full design context for the Consumer Markets SLM knowledge graph, starting with CPG. Read it before planning any work. `CLAUDE.md` holds the always-on rules; this file holds the reasoning and structure behind them.

---

## 1. Purpose and scope

We are building **one evolving knowledge graph** for the CPG (FMCG) sector that will ground a sector-specialised small language model (SLM). The graph is organised in six intelligence layers. The innermost layer, the CPG value chain, is the spine. Every outer layer enriches the same nodes rather than forming a separate graph.

The SLM must eventually answer multi-hop questions that document-only RAG cannot, for example:

> Which trade promotions generated distributor loading but failed to produce outlet-level sell-through or repeat consumer purchase?

That question traverses:
`TradePromotion → CustomerOrder → DistributorInventory → OutletAvailability → SellOutTransaction → PurchaseEvent → RepeatPurchase → PromotionSpend → Margin`

**Primary acceptance criterion:** successful multi-hop retrieval. Raw node count is not a success measure. A previous platform assessment found nodes generated without the relationships needed for connected queries, so connectedness is tested from day one.

**Scope of this build (quick MVP):**
- Layer 1 (value chain) fully modelled as a curated reference graph.
- Layer 2 finance processes overlaid from the existing Finance L3 ontology.
- Only the MVP commercial thread (Section 9) populated with instance data across Layers 3–6.
- Deeper enrichment of Layers 3–6 comes after the MVP.

---

## 2. The six-layer model

Enrichment logic, from inside out:

```
Sector value flow → operating processes → product and traceability
→ ecosystem and route-to-market → performance, risk and decisions
→ consumer behaviour and experience
```

| Layer | Question it answers | Core content |
|---|---|---|
| 1. Value chain | What value is created, and where does it flow? | 11 CPG stages, activities, inputs, outputs, events, decisions |
| 2. Functional processes | How is work executed? | Idea-to-launch, forecast-to-plan, source-to-contract, procure-to-pay, plan-to-produce, quality-to-release, order-to-cash, warehouse-to-delivery, campaign-to-conversion, trade-promotion management, record-to-report, hire-to-retire, risk-to-compliance, data-to-insight |
| 3. Product and asset | What is planned, produced and sold? | Brand, category, product family, formulation, recipe, ingredient, allergen, packaging spec, pack-price point, SKU, batch/lot, manufacturing line, plant, warehouse, finished good, shelf life, quality spec, product claim, certification |
| 4. Ecosystem and channel | Who participates, through which routes? | Ingredient and packaging suppliers, contract manufacturers, co-packers, 3PLs, C&F agents, distributors, sub-distributors, wholesalers, retailers, outlets, modern trade chains, e-commerce marketplaces, quick-commerce platforms, D2C, food service, geographies, micro-markets |
| 5. Performance and risk | What is happening, where to intervene? | Primary/secondary sales, sell-out, numeric and weighted distribution, on-shelf availability, inventory and freshness, forecast accuracy, OTIF, yield/waste/OEE, quality non-conformance, revenue and gross-to-net, trade-spend effectiveness, price realisation, margins, working capital, supplier/regulatory/sustainability risk |
| 6. Consumer and experience | Why is demand changing? | Consumer, household, segment, need state, consumption occasion, shopper mission, journey, touchpoint, basket, purchase event, consumption event, feedback, complaint, sentiment, preference, loyalty, advocacy, churn/switching |

---

## 3. Architecture principles

1. **One ontology, one connected graph.** Layers are tags on classes, not separate databases.
2. **Value-chain node first.** Every outer-layer object attaches to the spine through a declared hook relationship (Section 5.3). An outer-layer node with no path to a value-chain activity is a defect.
3. **Two ingestion lanes, never mixed.**
   - **Curated lane:** reference model data (value-chain stages, activities, process taxonomy, KPI definitions). Drafted with LLM help from source documents, reviewed by people, stored as YAML/CSV in `reference/`, every row cited.
   - **Extracted lane:** instance data (claims, invoices, promotions, outlets, sell-out) extracted from documents by LLM under strict "explicit only" rules, then validated and resolved before loading.
4. **Ontology YAML is the single source of truth.** DDL, Pydantic models, JSON schemas for extraction, validators and documentation are generated from it.
5. **Provenance on everything.** Every node and edge carries `source_system`, `source_record_id`, `source_reference`, `extraction_confidence` (curated rows use `1.0` and `lane: curated`).
6. **Engine-agnostic storage.** All graph access goes through a `GraphStore` interface so the engine can be swapped by changing one module.

---

## 4. Conventions

| Item | Convention | Example |
|---|---|---|
| Node labels | PascalCase | `ValueChainStage`, `PromotionClaim` |
| Relationship types | UPPER_SNAKE_CASE | `PRECEDES`, `CLAIMED_AGAINST` |
| Properties | snake_case | `claim_amount`, `valid_from` |
| IDs | Source ID if present; else `<EntityType>:<normalized_name>:<organization>:<period>` | `PromotionClaim:CLM8421` |
| Layer tag | Every class declares `layer: 1..6` (finance classes declare the layer they primarily serve, usually 2 or 5) | |
| Amounts | Stored exactly as stated; currency, unit, period stored separately; never rescaled | |

**Finance ontology migration:** the finance spec uses camelCase relationships (`contains`, `triggeredBy`, `claimedAgainst`). Convert mechanically to UPPER_SNAKE (`CONTAINS`, `TRIGGERED_BY`, `CLAIMED_AGAINST`) and keep a mapping table in `ontology/rel_name_map.yaml` so the original names remain traceable.

---

## 5. Layer 1 — CPG value-chain ontology

### 5.1 Core classes

`CPGValueChain`, `ValueChainStage`, `ValueChainActivity`, `Input`, `Output`, `BusinessEvent`, `Decision`, `DecisionOption`, `DecisionRule`, `ValueDriver`, `ValueOutcome`, `Constraint`, `Role`, `Organization`, `SourceEvidence`, `SubSector`

Each `ValueChainStage` carries: `definition`, `purpose`, `entry_event`, `exit_event`, `upstream_stage`, `downstream_stage`, plus links to inputs, outputs, decisions, value drivers, participants and source evidence.

`SubSector` (food & beverage, personal care, home care) lets stages and activities record where practice differs, via `VARIES_IN`.

### 5.2 Core relationships

```
(CPGValueChain)-[:CONTAINS]->(ValueChainStage)
(ValueChainStage)-[:PRECEDES]->(ValueChainStage)
(ValueChainStage)-[:CONTAINS]->(ValueChainActivity)
(ValueChainStage|ValueChainActivity)-[:VARIES_IN]->(SubSector)
(ValueChainActivity)-[:TRIGGERED_BY]->(BusinessEvent)
(ValueChainActivity)-[:CONSUMES]->(Input)
(ValueChainActivity)-[:PRODUCES]->(Output)
(ValueChainActivity)-[:REQUIRES]->(Decision)
(ValueChainActivity)-[:GOVERNED_BY]->(DecisionRule)
(ValueChainActivity)-[:PERFORMED_BY]->(Role)
(ValueChainActivity)-[:SUPPORTED_BY]->(Organization)
(ValueChainActivity)-[:INFLUENCES]->(ValueDriver)
(ValueChainActivity)-[:CREATES]->(ValueOutcome)
(ValueChainActivity)-[:CONSTRAINED_BY]->(Constraint)
(ValueChainActivity)-[:DEPENDS_ON]->(ValueChainActivity)
(ValueChainActivity)-[:SUPPORTED_BY_EVIDENCE]->(SourceEvidence)
(Output)-[:BECOMES_INPUT_TO]->(ValueChainActivity)
(Decision)-[:SELECTS]->(DecisionOption)
(ValueOutcome)-[:MEASURED_BY]->(KPI)
```

`FOLLOWS` is not stored; it is the reverse traversal of `PRECEDES`.

### 5.3 Cross-layer hook relationships

Declared in Phase 1 even before outer layers are populated, so later layers only add targets and never restructure the spine.

| Hook | From | To | Layer |
|---|---|---|---|
| `ENABLED_BY` | ValueChainActivity | ProcessGroup / L3ProcessEndpoint | 2 |
| `ACTS_ON` | ValueChainActivity | Brand, Category, SKU, Formulation, Batch, PackagingMaterial, Plant, Warehouse | 3 |
| `INVOLVES` | ValueChainActivity | Supplier, Customer, Distributor, Retailer, Outlet, Channel, LogisticsProvider | 4 |
| `MEASURED_BY` | ValueOutcome | KPI | 5 |
| `AFFECTS` | Risk | ValueChainActivity | 5 |
| `TOUCHES` | ValueChainActivity | ConsumerSegment, NeedState, Touchpoint | 6 |

### 5.4 The 11 stages

Flow: market signal → category opportunity → product concept → formulation → ingredient and packaging requirement → sourcing decision → production plan → batch → finished SKU → inventory → customer order → distributor/retailer → outlet availability → consumer purchase → consumption and feedback.

**Stage 1 — Consumer and market insight**
Purpose: identify changing needs, behaviours, occasions, category shifts and opportunities.
Activities: monitor consumer and category trends; analyse shopper and household behaviour; identify need states and occasions; analyse competitor products and claims; identify geographic and micro-market variation; estimate category opportunity; create opportunity hypotheses.
Inputs: consumer research, household panel, retail audit, search/social trends, complaints, competitor intelligence, sales and distribution data.
Outputs: consumer insight, need state, opportunity area, category growth hypothesis, target segment, demand signal.
Relationships: `ConsumerSegment HAS NeedState`; `NeedState OCCURS_IN ConsumptionOccasion`; `ConsumerInsight DERIVED_FROM ResearchStudy`; `ConsumerInsight IDENTIFIES OpportunityArea`; `OpportunityArea APPLIES_TO Category`; `OpportunityArea OBSERVED_IN Geography`; `OpportunityArea TARGETS ConsumerSegment`.

**Stage 2 — Portfolio and category strategy**
Purpose: translate opportunities into portfolio, category, brand and investment choices.
Activities: define category strategy; set brand role; identify portfolio gaps; rationalise portfolio; set innovation priorities; define price-pack architecture; allocate category investment; set launch/renovation priorities.
Outputs: category strategy, brand strategy, portfolio role, innovation brief, price-pack architecture, investment envelope.
Relationships: `CategoryStrategy APPLIES_TO Category`; `Brand PLAYS_ROLE_IN CategoryStrategy`; `Portfolio CONTAINS ProductFamily`; `PortfolioGap IDENTIFIED_IN Portfolio`; `InnovationPriority ADDRESSES OpportunityArea`; `PricePackArchitecture APPLIES_TO Channel`; `PricePackArchitecture CONTAINS PackPricePoint`.

**Stage 3 — Product innovation and formulation**
Purpose: convert an opportunity into a scalable, compliant product.
Activities: create concept; develop formulation/recipe; select ingredient alternatives; lab trials; performance testing; sensory validation; define claims; stability and shelf-life tests; regulatory review; approve specification.
Outputs: approved concept, formulation, recipe, ingredient spec, product claim, product spec, shelf-life definition, launch-ready SKU spec.
Relationships: `ProductConcept ADDRESSES NeedState`; `ProductConcept TARGETS ConsumerSegment`; `Formulation REALIZES ProductConcept`; `Formulation CONTAINS Ingredient`; `Ingredient CONFORMS_TO IngredientSpecification`; `Formulation PRODUCES ProductAttribute`; `ProductClaim SUPPORTED_BY TestResult`; `SKU BASED_ON Formulation`; `SKU HAS ProductSpecification`; `SKU HAS ShelfLife`; `SKU HAS RegulatoryStatus`.

**Stage 4 — Ingredient and packaging sourcing**
Purpose: secure qualified materials at the required cost, quality, lead time and risk.
Activities: translate formulation into material requirements; identify and qualify suppliers; run sourcing event; negotiate contract; assess supplier capacity; evaluate commodity exposure; approve ingredients and packaging; place PO; monitor inbound supply risk.
Outputs: approved supplier, ingredient contract, packaging contract, PO, material requirement, supplier risk assessment, commodity forecast.
Relationships: `Formulation REQUIRES Ingredient`; `SKU REQUIRES PackagingMaterial`; `Supplier SUPPLIES Ingredient|PackagingMaterial`; `Supplier QUALIFIED_FOR MaterialSpecification`; `SourcingEvent EVALUATES Supplier`; `Contract AWARDED_TO Supplier`; `PurchaseOrder REFERENCES Contract`; `PurchaseOrder ORDERS Material`; `CommodityPrice AFFECTS IngredientCost`; `SupplierRisk THREATENS MaterialAvailability`.

**Stage 5 — Manufacturing, quality and packaging**
Purpose: convert materials into compliant, saleable packaged goods.
Activities: production plan; production order; receive and release materials; batch/formulate; process, fill or form; in-process QC; package and label; finished-product testing; release or quarantine batch; record yield, loss, downtime.
Outputs: production batch, finished SKU, quality result, released batch, scrap/rework, manufacturing variance.
Relationships: `ProductionOrder PRODUCES Batch`; `Batch BASED_ON Formulation`; `Batch CONSUMES IngredientLot`; `Batch PRODUCED_AT Plant`; `Batch PRODUCED_ON ProductionLine`; `Batch PACKAGED_AS SKU`; `Batch HAS QualityResult`; `QualityResult TESTS QualitySpecification`; `Batch RELEASED_BY QualityRelease`; `Batch HAS Yield`; `Batch GENERATES Waste`; `DowntimeEvent AFFECTS ProductionLine`.

**Stage 6 — Demand, supply and inventory planning**
Purpose: balance expected demand, capacity, materials and inventory.
Activities: baseline forecast; promotion/event uplift; consensus forecast; supply plan; capacity planning; material requirements; inventory targets; constrained allocation; S&OP/IBP review; approve replenishment.
Outputs: demand forecast, consensus demand, supply plan, production requirement, inventory target, allocation decision, constrained forecast.
Relationships: `DemandForecast FORECASTS SKU|Geography|Channel`; `TradePromotion UPLIFTS DemandForecast`; `SupplyPlan SATISFIES DemandForecast`; `SupplyPlan REQUIRES ProductionCapacity|MaterialAvailability`; `InventoryPolicy SETS InventoryTarget`; `AllocationDecision ALLOCATES SKU`; `AllocationDecision PRIORITIZES Customer`.

**Stage 7 — Warehousing and distribution**
Purpose: position inventory and fulfil demand at required service level and cost.
Activities: receive finished goods; put away; allocate; pick and pack; plan transport; dispatch; deliver to distributor/retailer/fulfilment node; confirm proof of delivery; process returns; monitor freshness and expiry.
Outputs: inventory position, fulfilled order, shipment, delivery, POD, return, distribution cost.
Relationships: `FinishedGood STORED_AT Warehouse`; `InventoryPosition MEASURED_FOR SKU`; `InventoryPosition HELD_AT Location`; `CustomerOrder ALLOCATED_FROM InventoryPosition`; `Shipment FULFILLS CustomerOrder`; `Shipment ORIGINATES_AT Warehouse`; `Shipment DELIVERED_TO Customer`; `Shipment TRANSPORTED_BY LogisticsProvider`; `Delivery CONFIRMED_BY ProofOfDelivery`; `Return REFERENCES Delivery`.

**Stage 8 — Customer, channel and revenue growth**
Purpose: turn the portfolio into volume, revenue and margin through channel and customer choices.
Activities: segment customers; design route-to-market; set pricing and terms; joint business plans; plan promotions; create trade schemes; negotiate agreements; set sales targets; capture orders; manage distributor performance.
Outputs: channel strategy, customer plan, price condition, promotion, trade scheme, sales target, customer order.
Relationships: `RouteToMarket USES Channel`; `Channel SERVES ConsumerSegment`; `Distributor SERVES Outlet`; `CustomerPlan CREATED_FOR Customer`; `PriceCondition APPLIES_TO SKU|Customer`; `TradePromotion TARGETS Customer`; `TradePromotion APPLIES_TO SKU`; `TradePromotion VALID_IN Geography`; `SalesTarget ASSIGNED_TO Territory`; `CustomerOrder PLACED_BY Customer`.

**Stage 9 — Retail and outlet execution**
Purpose: convert distribution into availability, visibility and sell-through.
Activities: classify outlets; plan beats; visit outlets; capture orders; check inventory and on-shelf availability; execute assortment; verify planogram/display; activate promotions; track retailer scheme compliance; capture sell-out.
Outputs: outlet order, availability result, distribution measure, display compliance, promotion compliance, sell-out transaction, corrective action.
Relationships: `Outlet BELONGS_TO OutletType`; `Outlet LOCATED_IN MicroMarket`; `SalesRepresentative FOLLOWS BeatPlan`; `BeatPlan CONTAINS Outlet`; `Outlet STOCKS SKU`; `AvailabilityObservation OBSERVED_AT Outlet`; `AvailabilityObservation MEASURES SKU`; `Display EXECUTED_AT Outlet`; `Display SUPPORTS TradePromotion`; `SellOutTransaction OCCURS_AT Outlet`; `CorrectiveAction ADDRESSES ExecutionGap`.

**Stage 10 — Purchase, consumption and feedback**
Purpose: understand conversion from availability to purchase, usage, satisfaction and repeat.
Activities: discover; evaluate alternatives; purchase; consume/use; give feedback; complain; recommend/review; repurchase; switch.
Outputs: purchase event, consumption event, satisfaction signal, complaint, sentiment, loyalty indicator, switching signal.
Relationships: `Consumer PARTICIPATES_IN PurchaseEvent`; `PurchaseEvent CONTAINS SKU`; `PurchaseEvent OCCURS_AT Touchpoint`; `PurchaseEvent MOTIVATED_BY NeedState`; `SKU CONSUMED_IN ConsumptionOccasion`; `ConsumptionEvent GENERATES Feedback`; `Feedback EXPRESSES Sentiment`; `Complaint CONCERNS SKU`; `Complaint RELATES_TO_BATCH Batch`; `LoyaltyBehavior FOLLOWS PurchaseEvent`; `SwitchingEvent MOVES_FROM Brand`; `SwitchingEvent MOVES_TO Brand`.

**Stage 11 — Returns, waste and circularity**
Purpose: manage returns, packaging recovery, expiry, waste and sustainability.
Activities: process consumer/customer returns; identify damaged or expired product; recall affected batches; dispose or rework; recover packaging; recycle; measure waste; trace sustainability impact; corrective action.
Outputs: return disposition, product recall, disposal event, recycled material, waste measure, sustainability outcome, corrective action.
Relationships: `Return REFERENCES SKU|Batch`; `ProductRecall AFFECTS Batch`; `ProductRecall INITIATED_BY QualityIssue`; `Disposition DETERMINES ReturnOutcome`; `Waste GENERATED_BY Batch`; `Waste TREATED_BY DisposalMethod`; `PackagingMaterial RECOVERED_THROUGH RecoveryProgram`; `RecycledMaterial REPLACES PackagingMaterial`; `CorrectiveAction ADDRESSES RootCause`.

---

## 6. Layer 2 — Finance ontology overlay

The full Finance ontology spec lives in `docs/source/finance_extraction_spec.md` (the original extraction prompt, kept verbatim). The Finance L3 process catalogue lives in `docs/source/Consumer_Markets_Finance_Ontology_L3.xlsx` when available.

It covers 16 domains: finance strategy and performance; planning, budgeting and forecasting; record-to-report; order-to-cash; commercial finance; gross-to-net and trade investment; pricing and profitability; product costing; inventory accounting; procure-to-pay; treasury; tax; capex and fixed assets; financial reporting and analytics; finance risk and controls; finance data governance.

Class groups: process structure (FinanceDomain, ProcessGroup, L3ProcessEndpoint, TriggerEvent, ProcessOutput); organisation and responsibility; product, market and commercial dimensions; accounting structure; transactions and documents; planning and performance; commercial finance and trade promotion; product cost and inventory; receivables, payables, working capital; treasury; tax; assets and investment; reporting, risk, control and data.

How it connects to the spine:
- `L3ProcessEndpoint` is a graph node (not metadata) and attaches to value-chain activities via `ENABLED_BY`.
- Example: Manufacturing stage activities are `ENABLED_BY` Plan-to-Produce, Quality-to-Release, Maintain-to-Operate and Record-to-Report endpoints.
- Trade promotion accrual, claim settlement, product costing, inventory provisioning and profitability each attach to several stages (Stages 5–9).

### 6.1 Known defects in the finance spec and proposed resolutions

These must be resolved in Phase 1. Proposed defaults below; confirm with the project owner before applying anything marked *confirm*.

| Referenced but undeclared | Proposed resolution |
|---|---|
| `FiscalPeriod` | Declare (reference data: id, start, end, fiscal_year) |
| `Currency` | Declare (reference data: ISO code) |
| `Claim` | Map to `PromotionClaim` |
| `Provision` | Declare generic `Provision` with `provision_type` (receivable, tax, other) |
| `Reconciliation` | Declare with `reconciliation_type` |
| `Approval` | Declare |
| `Resolution` | Declare (closes APException) |
| `CostVariance` | Declare as Variance with `variance_type = cost` |
| `CostAllocation`, `Cost` | Replace with `AllocationRule ALLOCATES CostPool` *(confirm)* |
| `Sample`, `Retest` | Defer (out of MVP) |
| `Auditor` | Map to `Organization` with `organization_type = auditor` *(confirm)* |
| `Report` | Map to `ManagementReport` |
| `FinancialFact` | Map to `ActualResult` *(confirm)* |
| `Mapping` | Defer |
| `IntercompanyTransaction` | Declare (defer population) |
| `CarryingValue` | Property on `FixedAsset` |
| `CashGLBalance` | `Balance` on a cash account |
| `DecisionOption` (L1) | Declare |
| `BusinessFact` (L1) | Map to `SourceEvidence` or `ActualResult` *(confirm)* |
| Generic `Entity` in `CONSUMES`/`PRODUCES` | Restrict to an explicit allowed list of declared classes |

Other fixes:
- `JournalLine relatesTo` (SKU, Brand, Customer, Supplier, Channel, Geography) contradicts the "no generic relatesTo" rule. Rename to `ATTRIBUTED_TO`.
- `(Category)-[:belongsTo]->(Brand)` is wrong for CPG because brands span categories. Model Brand and Category as two independent hierarchies, both attached to ProductFamily/SKU: `ProductFamily BELONGS_TO_CATEGORY Category`, `ProductFamily BELONGS_TO_BRAND Brand`, `Category PARENT_OF Category`.
- Subtypes (`CostCentre isA ResponsibilityCentre`, VarianceDriver subtypes, CostComponent subtypes): the graph engine has no inheritance. Use a single table with a type property unless the subtypes carry different attributes.

---

## 7. External standards to anchor taxonomies

- **APQC PCF — Consumer Products edition** for Layer 2 process taxonomy alignment. It is co-developed with IBM under specific license terms; check the license before embedding PCF text in client-facing outputs. Store only PCF IDs and our own labels until cleared.
- **GS1 Global Product Classification (GPC)** for Layer 3 category taxonomy: Segment → Family → Class → Brick. Relevant CPG segments include Food/Beverage/Tobacco, Cleaning/Hygiene Products, and Beauty/Personal Care/Hygiene. Store `gpc_brick_code` on Category or ProductFamily.

---

## 8. Storage

- **Engine:** LadybugDB (community fork of Kuzu after Kuzu was archived in Oct 2025), Python package `real_ladybug`. Embedded, Cypher, typed schema, full-text and vector indices.
- **Fallback:** Kuzu 0.11.3 pinned. Note that Ladybug may not open older Kuzu database files; always rebuild from source data, never copy DB files across engines.
- **Abstraction:** `graph/store.py` defines `GraphStore` (connect, apply_ddl, bulk_load, query, close). Only `graph/backends/*.py` imports the engine.
- **Loading:** bulk `COPY FROM` parquet files written by the pipeline. No row-by-row inserts for bulk data.
- **Schema:** node tables have a `STRING PRIMARY KEY id`. A relationship name reused across several class pairs (e.g., `CONTAINS`) is one rel table declaring multiple FROM–TO pairs.
- **Eventual target:** the firm's in-house KG console may be the production home. Keep an export path (CSV/JSON of nodes and edges + ontology) so the graph can be ingested there.

---

## 9. MVP boundary — the commercial thread

```
Consumer insight → demand forecast → SKU and pack → distributor → outlet
→ promotion → availability → sell-out → margin → consumer response
```

Priority stages for instance data: 1 (insight), 6 (planning), 8 (customer, channel, RGM), 9 (outlet execution), 10 (purchase and feedback).

Priority entities: Brand, Category, SKU, PackPricePoint, ConsumerSegment, NeedState, Geography, MicroMarket, Channel, Distributor, Retailer, Outlet, DemandForecast, InventoryPosition, TradePromotion, PromotionClaim, CustomerOrder, AvailabilityObservation, SellOutTransaction, PurchaseEvent, TradeSpend, Margin, KPI, SourceEvidence.

Priority relationships: BELONGS_TO_*, TARGETS, APPLIES_TO, FORECASTS, STOCKS, LOCATED_IN, SERVES, PLACED_BY, FULFILLS, OBSERVED_AT, MEASURES, OCCURS_AT, GENERATES, REDUCES, IMPACTS, DERIVED_FROM, CLAIMED_AGAINST, SUBMITTED_BY, SETTLES, SUPPORTED_BY_EVIDENCE.

**Data for the MVP:** real client material may not be cleared for external model APIs. Build and test against a **synthetic CPG dataset** for a fictional company (2 brands, 3 categories, ~30 SKUs, 3 channels incl. GT/MT/quick commerce, ~10 distributors, ~200 outlets in 3 micro-markets, 6 promotions over 2 quarters, with deliberately planted patterns such as a promotion that loaded distributors but did not sell through). Synthetic data lives in `data/synthetic/` and is generated by a seeded script.

---

## 10. Pipeline design

### 10.1 Curated lane (Layer 1, process taxonomy, KPI definitions)
1. Draft rows in `reference/*.yaml` from source docs, each with `source_reference`.
2. Human review (owner marks `reviewed: true`).
3. Validate against ontology → write parquet → load.

### 10.2 Extracted lane (instance data)
1. **Chunk** source documents; record file/page/section for provenance.
2. **Route** each chunk to the relevant ontology slice (e.g., order-to-cash, trade promotion) so the model only sees the classes it needs.
3. **Extract** with an LLM forced to return output matching a JSON schema generated from the ontology (tool/function call with schema, not "please return JSON"). The LLM client is pluggable (`extract/llm_client.py`) so it can point at an approved endpoint.
4. **Validate**: schema conformance, required attributes, Section-4 constraints from the finance spec, allowed FROM–TO pairs, no orphan nodes. Failures go to `staging/rejected/` with reasons; ambiguous text goes to `unresolved_items`.
5. **Resolve** entities: exact source ID → canonical alias table → fuzzy match above threshold → human review queue. Never auto-merge the pairs listed as "do not merge" in the finance spec (Customer/Consumer, Brand/ProductFamily, Channel/Customer, Budget/Forecast, Claim/Deduction, Risk/Issue, Control/Process, etc.).
6. **Load** via parquet bulk copy.

### 10.3 Quality metrics (reported by `make report`)
- Orphan node rate (target 0 for curated lane, < 5% for extracted)
- Edges per node by class
- Share of outer-layer nodes with a path to a ValueChainActivity
- Validation rejection rate by reason
- Unresolved item count

---

## 11. Retrieval and SLM readiness

- **Hybrid retrieval:** exact ID lookup → name/alias full-text → vector similarity over descriptions → graph traversal with dimensional filters (period, geography, channel, brand).
- **Competency questions** (Section 12) are pytest cases with expected results on synthetic data. They are both the spec and the regression suite.
- **Training data for the SLM** is generated from the graph, not written by hand: per-node definition Q&A, adjacency Q&A (upstream/downstream), path explanations for multi-hop questions, and sub-sector variation questions. Output JSONL with provenance per pair. The graph supplies facts at inference; training teaches vocabulary and structure.

---

## 12. Competency questions

Layer 1 (Phase 1):
1. Which stage does "trade scheme creation" belong to, and what are its upstream and downstream stages?
2. What outputs of Stage 3 become inputs to Stage 4?
3. Which activities depend on the consensus demand forecast?
4. How does Stage 5 differ between food & beverage and home care?

Cross-layer (Phases 2–3):
5. Which finance L3 processes enable outlet execution activities?
6. Which trade promotions loaded distributors but did not produce outlet sell-through?
7. For promotion X, what was claimed, approved and settled, against which invoices and SKUs?
8. Which micro-markets show low on-shelf availability for SKUs under active promotion?
9. Which SKUs have declining margin driven by rising trade spend?
10. Which consumer complaints trace back to a specific batch and plant?

---

## 13. Phase plan

Three phases. Each starts in plan mode and ends with its exit criteria green.

### Phase 1 — Foundation and value-chain spine
- Repo scaffold, uv environment, Makefile (`gen`, `validate`, `load`, `test`, `report`).
- Ontology YAML for Layer 1 + finance (converted names, fixes from Section 6.1, layer tags, hook relationships).
- Codegen: DDL, Pydantic models, JSON schemas, `rel_name_map.yaml`.
- `GraphStore` interface + LadybugDB backend.
- Curated Layer-1 reference data: 11 stages, 60–80 activities, inputs/outputs/events/decisions, sub-sector variations, citations.
- Validators + orphan check; Claude Code hook, subagents and extraction skill set up.
- **Exit:** `make validate` green, zero undeclared classes, Layer-1 graph loaded, competency questions 1–4 pass.

### Phase 2 — Finance overlay and MVP extraction
- Ingest Finance L3 endpoints; map to value-chain activities with `ENABLED_BY`.
- Seeded synthetic CPG dataset generator with planted patterns.
- Extraction pipeline (chunk → route → extract → validate → resolve → load), run on synthetic documents.
- **Exit:** MVP entities loaded with provenance, orphan rate within target, competency questions 5–7 pass.

### Phase 3 — Retrieval and SLM readiness
- Hybrid retrieval module + simple CLI (`kg ask "..."`) that returns answer paths with provenance.
- Remaining competency questions as tests.
- Training-pair generator → `exports/training/v0.jsonl`; graph export for the in-house console.
- **Exit:** competency questions 1–10 pass on synthetic data, training set v0 exported, export round-trips.

After Phase 3: deepen Layers 3–6 one at a time using the same pattern (competency questions → ontology additions through hooks → ingestion → tests).

---

## 14. Repository structure

```
cpg-kg/
├── CLAUDE.md
├── Makefile
├── pyproject.toml
├── docs/
│   ├── PROJECT_CONTEXT.md          # this file
│   ├── DECISIONS.md                # running log of design decisions
│   └── source/                     # original specs and source material, verbatim
├── ontology/                       # SOURCE OF TRUTH
│   ├── layer1_value_chain.yaml
│   ├── finance.yaml
│   ├── hooks.yaml
│   └── rel_name_map.yaml
├── gen/                            # generated — never hand-edit
├── reference/                      # curated lane data (YAML/CSV, cited, reviewed flag)
├── data/synthetic/                 # seeded synthetic dataset
├── extract/                        # chunking, routing, LLM client, extraction
├── validate/                       # schema + constraint + orphan checks
├── resolve/                        # entity resolution + review queue
├── graph/                          # GraphStore interface + backends
├── retrieve/                       # hybrid retrieval, CLI
├── exports/                        # training JSONL, console export
├── staging/                        # extraction outputs, rejected, unresolved
├── tests/
│   ├── unit/
│   └── competency/
└── .claude/
    ├── settings.json               # hooks
    ├── agents/                     # ontology-reviewer, cypher-tester
    └── skills/kg-extraction/       # extraction rules skill
```

---

## 15. Data handling

Source material may include client correspondence and internal decks. Do not send real client documents to any external model API unless the project owner confirms it is permitted. Default to synthetic data and to the pluggable LLM client. Never commit real client data; `docs/source/` holds specs only, and real data paths are gitignored.

---

## 16. Open decisions (ask the owner, log answers in DECISIONS.md)

1. Items marked *confirm* in Section 6.1.
2. Which LLM endpoint is approved for extraction on real data.
3. Whether the production home is the in-house KG console (affects export format).
4. APQC PCF licence clearance for client-facing use.
