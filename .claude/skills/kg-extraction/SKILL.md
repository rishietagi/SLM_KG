---
name: kg-extraction
description: Extraction rules for the CPG Intelligence Graph — use for anything touching extraction prompts, extraction JSON schemas, staging outputs, entity resolution or the extracted lane (Phase 2+). Adapts docs/source/finance_extraction_spec.md to the project's naming conventions and two-lane design.
---

# KG extraction rules

Source of these rules: `docs/source/finance_extraction_spec.md` (verbatim, camelCase). This skill is the
**operative** version: canonical names come from `ontology/*.yaml`, never from the spec text.

## Two lanes — never mixed
- **Curated lane** (`reference/`): reference-model rows (stages, activities, process taxonomy, KPI definitions). Human-reviewed (`reviewed: true` set by the owner). Not produced by extraction.
- **Extracted lane** (`staging/`): instance data (claims, invoices, promotions, outlets, sell-out). Pipeline: chunk → route → extract → validate → resolve → load. Every row carries `lane: extracted`.
- Extraction output goes to `staging/`; failures to `staging/rejected/` with a reason; ambiguity to `staging/unresolved/`. Nothing is loaded without passing `make validate`.

## Output contract
- The LLM must be forced to the JSON schema `gen/json_schema/extraction_output.json` (tool/function call with schema — never "please return JSON"). Regenerate with `make gen`; never hand-edit `gen/`.
- Envelope (spec §7): `entities[]`, `relationships[]`, `unresolved_items[]`, `validation_results`.
- `entity_type` ∈ declared classes (PascalCase). `relationship` ∈ declared relationships (UPPER_SNAKE). The (subject_type, relationship, object_type) triple must be an allowed pair (`x-allowed-pairs` in the schema).
- Attribute keys are snake_case as declared in the ontology (e.g. `claim_amount`, not `claimAmount`). The spec's `...ID` attribute becomes the entity `id`.

## Extraction principles (spec §1, adapted)
1. Extract only what is explicitly stated. No entities or edges from assumption or inference.
2. Never calculate, rescale or modify amounts. Store the number in the attribute (e.g. `claim_amount: 620000`) **and** the exact source text in its `_text` companion (`claim_amount_text: "INR 620,000"`). Currency, unit and period go in their own fields.
3. Every entity has a stable id: the source identifier if present, else `<EntityType>:<normalized_name>:<organization>:<period>`.
4. Every node and edge carries provenance: `source_system`, `source_record_id`, `source_reference` (file/page/sheet/row/section), `extraction_confidence` (0–1), `lane: extracted`, `reviewed: false`.
5. Ambiguous statements go to `unresolved_items` with `source_text`, `reason`, `candidate_entity_types`, `candidate_relationships`. Do not force a relationship.
6. Never use a generic relationship (`RELATES_TO`, `LINKED_TO`). The finance spec's `relatesTo` is renamed: JournalLine → `ATTRIBUTED_TO`; Deduction→SalesInvoice `TAKEN_AGAINST`; Dispute→Deduction `CONTESTS`; APException→SupplierInvoice `RAISED_ON`.
7. `L3ProcessEndpoint` is a node, not metadata; it attaches to value-chain activities via `ENABLED_BY`.
8. Connect each financial fact to available dimensions (organization, legal entity, business unit, responsibility centre, account, SKU, brand/category, customer/supplier, channel, geography, fiscal period, currency) — only where the source states them.
9. Every extracted outer-layer node must have a path to a `ValueChainActivity`; orphans fail validation.

## Name conversion
Spec names are camelCase; canonical names are UPPER_SNAKE. Look up any spec name in `ontology/rel_name_map.yaml` (it records renames, class mappings, retargets, deferrals and drops). Key mappings:
`claimedAgainst → CLAIMED_AGAINST`, `submittedBy → SUBMITTED_BY`, `settles → SETTLES`, `offeredTo → TARGETS`,
TradePromotion `operatesIn → VALID_IN`, `ProductFamily belongsTo Category → BELONGS_TO_CATEGORY`, plus `BELONGS_TO_BRAND` (brand and category are independent hierarchies — never Category→Brand).
Class mappings: Claim→PromotionClaim, Auditor→Organization(`organization_type: auditor`), Report→ManagementReport, FinancialFact→ActualResult, CashGLBalance→Balance, CostVariance→Variance(`variance_type: cost`), Price/Volume/MixVariance→VarianceDriver(`driver_type`). Sample, Retest, Mapping are deferred — send to `unresolved_items`.

## Entity resolution (spec §5)
- Label normalisation: "company/legal company/reporting entity" → LegalEntity (statutory context); "item/material/product code" → SKU (with a stock-keeping id); "account/GL account/ledger account" → FinancialAccount; "promotion/scheme/trade scheme/customer scheme" → TradePromotion; "claim/scheme claim/promotion claim" → PromotionClaim; "actual/actual result/reported result" → ActualResult; "plan" → Budget only for an approved financial plan, otherwise unresolved.
- Order: exact source id → canonical alias table → fuzzy match above threshold → human review queue.
- Keep every alternative label in `aliases` and the original in `source_label`.
- **Never auto-merge**: Customer/Consumer, Brand/ProductFamily, Category/SKU, Channel/Customer, CostCentre/ProfitCentre, Budget/Forecast, TradePromotion/Discount, PromotionClaim/Deduction, Risk/Issue, Control/L3ProcessEndpoint (`ontology/common.yaml: do_not_merge`).
- A distributor that submits a claim is extracted as `Customer` (spec §8 example). `Distributor` is a separate Layer-4 class; the account links to it with `Customer ACCOUNT_OF Distributor` (DECISIONS D38), which comes from the structured master feed.

## Constraints to validate (spec §4, canonical names)
Checked on the resolved entity, not per document (D44). Missing non-core "required" attributes are warnings.
- L3ProcessEndpoint: exactly one ProcessGroup (CONTAINS), ≥1 TRIGGERED_BY TriggerEvent, ≥1 PRODUCES.
- JournalEntry: ≥2 JournalLines, one ORIGINATES_IN SourceSystem, a LegalEntity and FiscalPeriod.
- JournalLine: one POSTS_TO FinancialAccount, amount, debit_credit_indicator, one DENOMINATED_IN Currency, RECORDED_FOR LegalEntity, OCCURRED_DURING FiscalPeriod.
- Budget/Forecast: version, COVERS FiscalPeriod, ≥1 dimension.
- Variance: two compared results, variance_type, value + unit, CAUSED_BY VarianceDriver where stated.
- KPI: business_definition, formula, unit, owner where stated.
- TradePromotion: start_date and end_date; APPLIES_TO/TARGETS/EXECUTED_IN ≥1 SKU, Brand, Customer or Channel; FUNDS from PromotionBudget where available.
- PromotionClaim: SUBMITTED_BY Customer, CLAIMED_AGAINST TradePromotion, claim_amount and status, SUPPORTED_BY Evidence where available.
- Control: MITIGATES ≥1 Risk, owner, frequency, control_type.
- Every amount: value, currency, period or date, source_reference.

## Worked example (spec §8, canonical form)
"Distributor D107 submitted claim CLM8421 for INR 620,000 against promotion TP2026-045 for SKU Detergent-1KG. INR 510,000 was approved and settled through credit note CN7311 against invoice INV96100."
Entities: `Customer:D107`, `PromotionClaim:CLM8421` (`claim_amount: 620000`, `claim_amount_text: "INR 620,000"`, `approved_amount: 510000`, `currency: INR`), `TradePromotion:TP2026-045`, `SKU:Detergent-1KG`, `CreditNote:CN7311`, `SalesInvoice:INV96100`, `Currency:INR`.
Edges: `(PromotionClaim:CLM8421)-[:SUBMITTED_BY]->(Customer:D107)`, `-[:CLAIMED_AGAINST]->(TradePromotion:TP2026-045)`, `-[:REFERENCES]->(SKU:Detergent-1KG)`, `-[:REFERENCES]->(SalesInvoice:INV96100)`; `(CreditNote:CN7311)-[:SETTLES]->(PromotionClaim:CLM8421)`, `(CreditNote:CN7311)-[:REDUCES]->(SalesInvoice:INV96100)`.

## Data handling
Default to `data/synthetic/`. Do not send real client documents to an external model API unless `docs/DECISIONS.md` records approval. Never commit real client data.

## Pipeline commands (Phase 2)
`make synth` (synthetic data) → `make stage` (tabular feeds) → `make extract` (documents; `KG_LLM=gemini` for live calls,
default `replay`) → `make validate` → `make resolve` → `make load` → `make report`. Slices: `ontology/slices.yaml`;
LLM schemas: `gen/json_schema/slices/`; prompts: `extract/prompts.py`.
