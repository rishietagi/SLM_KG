# CPG Value Chain Design Notes

The slide is directionally right: the value chain should be the spine of the CPG SLM, and the circular layers should progressively enrich the same nodes rather than become six separate knowledge graphs. This is also consistent with the existing Consumer Markets design, which explicitly describes enrichment from core sector structure to execution context, product detail, ecosystem relationships, performance signals and consumer intelligence. [CM SLM - 02092026 | PowerPoint], [CM SLM - 1...der's Note | PowerPoint], [CM SLM - 1...ernal Deck | PowerPoint]

For CPG, however, the inner value-chain ring should be changed from the current Consumer Durables language. Terms such as "design and engineering," "installation and usage," and "after-sales and circularity" fit durables better than packaged goods. A CPG value chain should explicitly represent consumer insight, formulation, ingredients, packaging, manufacturing, route-to-market, retail execution and consumption.

## 1. Recommended CPG six-layer model

### Layer 1: CPG value chain
What value is created, and where does it flow?
- Consumer and market insight
- Portfolio and category strategy
- Product innovation and formulation
- Ingredient and packaging sourcing
- Manufacturing, quality and packaging
- Demand, supply and inventory planning
- Warehousing and distribution
- Channel, customer and revenue growth management
- Retail and outlet execution
- Consumer purchase, consumption and feedback
- Returns, waste and circularity

### Layer 2: Functional processes
How is work executed across the value chain?
- Idea-to-launch
- Forecast-to-plan
- Source-to-contract
- Procure-to-pay
- Plan-to-produce
- Quality-to-release
- Order-to-cash
- Warehouse-to-delivery
- Campaign-to-conversion
- Trade-promotion management
- Record-to-report
- Hire-to-retire
- Risk-to-compliance
- Data-to-insight

### Layer 3: Product and asset
What is being planned, produced and sold?
- Brand
- Category
- Product family
- Formulation
- Recipe
- Ingredient
- Allergen
- Packaging specification
- Pack and price point
- SKU
- Batch and lot
- Manufacturing line
- Plant
- Warehouse
- Finished good
- Shelf life
- Quality specification
- Product claim
- Certification

### Layer 4: Ecosystem and channel
Who participates, and through which routes to market?
- Ingredient suppliers
- Packaging suppliers
- Contract manufacturers
- Plants and co-packers
- Third-party logistics providers
- Carrying and forwarding agents
- Distributors
- Sub-distributors
- Wholesalers
- Retailers
- Outlets
- Modern trade chains
- E-commerce marketplaces
- Quick-commerce platforms
- D2C channels
- Food-service customers
- Geographies and micro-markets

### Layer 5: Performance and risk
What is happening, and where is intervention required?
- Primary sales
- Secondary sales
- Sell-out
- Numeric and weighted distribution
- On-shelf availability
- Inventory and freshness
- Forecast accuracy
- Service level and OTIF
- Yield, waste and OEE
- Quality and non-conformance
- Revenue and gross-to-net
- Trade-spend effectiveness
- Price realization
- Gross and contribution margin
- Working capital
- Supplier, regulatory and sustainability risk

### Layer 6: Consumer and experience
Why is demand changing?
- Consumer
- Household
- Segment
- Need state
- Consumption occasion
- Shopper mission
- Journey
- Touchpoint
- Basket
- Purchase event
- Consumption event
- Feedback
- Complaint
- Sentiment
- Preference
- Loyalty
- Advocacy
- Churn or switching

The existing internal CPG material supports this direction. It identifies formulation, packaging, demand forecasting, procurement analytics, manufacturing optimization, distribution, inventory, trade schemes, outlet execution and consumer insight as connected parts of the FMCG value chain. External CPG descriptions similarly cover raw-material sourcing, product development, manufacturing, packaging, distribution, marketing and sales, and after-sales support. [FW: AI use...n at Emami | Outlook] [flevy.com], [flevy.com]

## 2. Layer 1 should be the first build

Do not begin by constructing all six layers at equal depth. Start with the CPG value-chain skeleton, because it gives the SLM a stable reasoning path:

```
Market signal
→ category opportunity
→ product concept
→ formulation
→ ingredient and packaging requirement
→ sourcing decision
→ production plan
→ batch
→ finished SKU
→ inventory
→ customer order
→ distributor or retailer
→ outlet availability
→ consumer purchase
→ consumption and feedback
```

This creates the core graph on which the other layers can attach.

### Proposed Layer 1 hierarchy

```
CPGValueChain
├── 1. Consumer and Market Insight
├── 2. Portfolio and Category Strategy
├── 3. Product Innovation and Formulation
├── 4. Ingredient and Packaging Sourcing
├── 5. Manufacturing, Quality and Packaging
├── 6. Demand, Supply and Inventory Planning
├── 7. Warehousing and Distribution
├── 8. Customer, Channel and Revenue Growth
├── 9. Retail and Outlet Execution
├── 10. Purchase, Consumption and Feedback
└── 11. Returns, Waste and Circularity
```

Each stage needs to be represented as a graph node with:
- Definition
- Entry event
- Exit event
- Inputs
- Outputs
- Decisions
- Value drivers
- Participants
- Downstream stage
- Upstream stage
- Relevant source evidence

## 3. Value-chain ontology

### Core value-chain entities

```
CPGValueChain
ValueChainStage
ValueChainActivity
Input
Output
BusinessEvent
Decision
DecisionRule
ValueDriver
ValueOutcome
Constraint
Dependency
Role
Organization
SourceEvidence
```

### Canonical relationships

```
(CPGValueChain)-[:CONTAINS]->(ValueChainStage)

(ValueChainStage)-[:PRECEDES]->(ValueChainStage)
(ValueChainStage)-[:FOLLOWS]->(ValueChainStage)

(ValueChainStage)-[:CONTAINS]->(ValueChainActivity)

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
(Decision)-[:BASED_ON]->(BusinessFact)
(ValueOutcome)-[:MEASURED_BY]->(KPI)
```

## 4. CPG value-chain stages in detail

### Stage 1: Consumer and market insight

**Purpose:** Identify changing needs, behaviours, occasions, category shifts and market opportunities.

**Activities**
- Monitor consumer and category trends
- Analyze shopper and household behaviour
- Identify need states and consumption occasions
- Analyze competitive products and claims
- Identify geographic and micro-market variation
- Estimate category opportunity
- Create opportunity hypotheses

**Inputs**
- Consumer research
- Household-panel data
- Retail audit data
- Search and social trends
- Complaints and feedback
- Competitor intelligence
- Sales and distribution data

**Outputs**
- Consumer insight
- Need state
- Opportunity area
- Category growth hypothesis
- Target segment
- Demand signal

**Core relationships**
```
ConsumerSegment HAS NeedState
NeedState OCCURS_IN ConsumptionOccasion
ConsumerInsight DERIVED_FROM ResearchStudy
ConsumerInsight IDENTIFIES OpportunityArea
OpportunityArea APPLIES_TO Category
OpportunityArea OBSERVED_IN Geography
OpportunityArea TARGETS ConsumerSegment
```

### Stage 2: Portfolio and category strategy

**Purpose:** Translate market opportunities into portfolio, category, brand and investment choices.

**Activities**
- Define category strategy
- Set brand role
- Identify portfolio gaps
- Rationalize product portfolio
- Set innovation priorities
- Define price-pack architecture
- Allocate category investment
- Determine launch or renovation priorities

**Outputs**
- Category strategy
- Brand strategy
- Portfolio role
- Innovation brief
- Price-pack architecture
- Investment envelope

**Relationships**
```
CategoryStrategy APPLIES_TO Category
Brand PLAYS_ROLE_IN CategoryStrategy
Portfolio CONTAINS ProductFamily
PortfolioGap IDENTIFIED_IN Portfolio
InnovationPriority ADDRESSES OpportunityArea
PricePackArchitecture APPLIES_TO Channel
PricePackArchitecture CONTAINS PackPricePoint
```

### Stage 3: Product innovation and formulation

**Purpose:** Convert a consumer opportunity into a scalable, compliant product.

**Activities**
- Create product concept
- Develop formulation or recipe
- Select ingredient alternatives
- Conduct laboratory trials
- Test product performance
- Validate sensory attributes
- Define product claims
- Conduct stability and shelf-life tests
- Complete regulatory review
- Approve product specification

**Outputs**
- Approved product concept
- Formulation
- Recipe
- Ingredient specification
- Product claim
- Product specification
- Shelf-life definition
- Launch-ready SKU specification

**Relationships**
```
ProductConcept ADDRESSES NeedState
ProductConcept TARGETS ConsumerSegment
Formulation REALIZES ProductConcept
Formulation CONTAINS Ingredient
Ingredient CONFORMS_TO IngredientSpecification
Formulation PRODUCES ProductAttribute
ProductClaim SUPPORTED_BY TestResult
SKU BASED_ON Formulation
SKU HAS ProductSpecification
SKU HAS ShelfLife
SKU HAS RegulatoryStatus
```

CPG requires formulation and recipe entities that are not relevant in the same way to Consumer Durables. Internal material specifically identifies product formulation, trend capture, smart packaging and market-readiness testing as connected R&D concerns. [FW: AI use...n at Emami | Outlook]

### Stage 4: Ingredient and packaging sourcing

**Purpose:** Secure qualified materials at the required cost, quality, lead time and risk level.

**Activities**
- Translate formulation into material requirements
- Identify and qualify suppliers
- Conduct sourcing event
- Negotiate contract and commercial terms
- Assess supplier capacity
- Evaluate commodity exposure
- Approve ingredients and packaging
- Place purchase order
- Monitor inbound supply risk

**Outputs**
- Approved supplier
- Ingredient contract
- Packaging contract
- Purchase order
- Material requirement
- Supplier risk assessment
- Commodity forecast

**Relationships**
```
Formulation REQUIRES Ingredient
SKU REQUIRES PackagingMaterial
Supplier SUPPLIES Ingredient
Supplier SUPPLIES PackagingMaterial
Supplier QUALIFIED_FOR MaterialSpecification
SourcingEvent EVALUATES Supplier
Contract AWARDED_TO Supplier
PurchaseOrder REFERENCES Contract
PurchaseOrder ORDERS Material
CommodityPrice AFFECTS IngredientCost
SupplierRisk THREATENS MaterialAvailability
```

### Stage 5: Manufacturing, quality and packaging

**Purpose:** Convert materials into compliant, saleable packaged goods.

**Activities**
- Create production plan
- Issue production order
- Receive and release materials
- Batch or formulate product
- Process, fill or form product
- Perform in-process quality checks
- Package and label
- Conduct finished-product testing
- Release or quarantine batch
- Record yield, loss and downtime

**Outputs**
- Production batch
- Finished SKU
- Quality result
- Released batch
- Scrap or rework
- Manufacturing variance

**Relationships**
```
ProductionOrder PRODUCES Batch
Batch BASED_ON Formulation
Batch CONSUMES IngredientLot
Batch PRODUCED_AT Plant
Batch PRODUCED_ON ProductionLine
Batch PACKAGED_AS SKU
Batch HAS QualityResult
QualityResult TESTS QualitySpecification
Batch RELEASED_BY QualityRelease
Batch HAS Yield
Batch GENERATES Waste
DowntimeEvent AFFECTS ProductionLine
```

Externally, CPG manufacturing is commonly described as raw-material receipt and quality release, formulation or batching, primary production, packaging and labelling, and warehousing before distribution. [kaizen.com]

### Stage 6: Demand, supply and inventory planning

**Purpose:** Balance expected demand, available capacity, materials and inventory.

**Activities**
- Generate baseline forecast
- Add promotion and event uplift
- Create consensus forecast
- Develop supply plan
- Conduct capacity planning
- Calculate material requirement
- Set inventory target
- Allocate constrained supply
- Conduct S&OP or IBP review
- Approve replenishment plan

**Outputs**
- Demand forecast
- Consensus demand
- Supply plan
- Production requirement
- Inventory target
- Allocation decision
- Constrained forecast

**Relationships**
```
DemandForecast FORECASTS SKU
DemandForecast FORECASTS Geography
DemandForecast FORECASTS Channel
Promotion UPLIFTS DemandForecast
SupplyPlan SATISFIES DemandForecast
SupplyPlan REQUIRES ProductionCapacity
SupplyPlan REQUIRES MaterialAvailability
InventoryPolicy SETS InventoryTarget
AllocationDecision ALLOCATES SKU
AllocationDecision PRIORITIZES Customer
```

### Stage 7: Warehousing and distribution

**Purpose:** Position inventory and fulfil customer demand at the required service level and cost.

**Activities**
- Receive finished goods
- Put away inventory
- Allocate inventory
- Pick and pack orders
- Plan transport
- Dispatch shipment
- Deliver to distributor, retailer or fulfilment location
- Confirm proof of delivery
- Process returns
- Monitor freshness and expiry

**Outputs**
- Inventory position
- Fulfilled order
- Shipment
- Delivery
- Proof of delivery
- Return
- Distribution cost

**Relationships**
```
FinishedGood STORED_AT Warehouse
InventoryPosition MEASURED_FOR SKU
InventoryPosition HELD_AT Location
CustomerOrder ALLOCATED_FROM InventoryPosition
Shipment FULFILLS CustomerOrder
Shipment ORIGINATES_AT Warehouse
Shipment DELIVERED_TO Customer
Shipment TRANSPORTED_BY LogisticsProvider
Delivery CONFIRMED_BY ProofOfDelivery
Return REFERENCES Delivery
```

### Stage 8: Customer, channel and revenue growth

**Purpose:** Translate the portfolio into volume, revenue and margin through channel and customer choices.

**Activities**
- Segment customers
- Design route-to-market
- Set pricing and terms
- Develop joint business plan
- Plan promotion
- Create trade scheme
- Negotiate customer agreement
- Set sales target
- Generate or capture order
- Manage distributor performance

**Outputs**
- Channel strategy
- Customer plan
- Price condition
- Promotion
- Trade scheme
- Sales target
- Customer order

**Relationships**
```
RouteToMarket USES Channel
Channel SERVES ConsumerSegment
Distributor SERVES Outlet
CustomerPlan CREATED_FOR Customer
PriceCondition APPLIES_TO SKU
PriceCondition APPLIES_TO Customer
TradePromotion TARGETS Customer
TradePromotion APPLIES_TO SKU
TradePromotion VALID_IN Geography
SalesTarget ASSIGNED_TO Territory
CustomerOrder PLACED_BY Customer
```

### Stage 9: Retail and outlet execution

**Purpose:** Convert distribution into availability, visibility and sell-through.

**Activities**
- Classify outlet
- Plan sales beat
- Visit outlet
- Capture order
- Check inventory
- Check on-shelf availability
- Execute assortment
- Verify planogram or display
- Activate promotion
- Track retailer scheme compliance
- Capture sell-out signal

**Outputs**
- Outlet order
- Availability result
- Distribution measure
- Display compliance
- Promotion compliance
- Sell-out transaction
- Corrective action

**Relationships**
```
Outlet BELONGS_TO OutletType
Outlet LOCATED_IN MicroMarket
SalesRepresentative FOLLOWS BeatPlan
BeatPlan CONTAINS Outlet
Outlet STOCKS SKU
AvailabilityObservation OBSERVED_AT Outlet
AvailabilityObservation MEASURES SKU
Display EXECUTED_AT Outlet
Display SUPPORTS TradePromotion
SellOutTransaction OCCURS_AT Outlet
CorrectiveAction ADDRESSES ExecutionGap
```

Internal CPG material explicitly links channel-partner performance, distributor management, beat optimization, outlet classification, trade schemes, inventory, fulfilment and location-based analytics. [FW: AI use...n at Emami | Outlook]

### Stage 10: Purchase, consumption and feedback

**Purpose:** Understand conversion from product availability to consumer purchase, usage, satisfaction and repeat behaviour.

**Activities**
- Discover product
- Evaluate alternatives
- Purchase product
- Consume or use product
- Provide feedback
- Submit complaint
- Recommend or review
- Repurchase
- Switch product or brand

**Outputs**
- Purchase event
- Consumption event
- Satisfaction signal
- Complaint
- Sentiment
- Loyalty indicator
- Switching signal

**Relationships**
```
Consumer PARTICIPATES_IN PurchaseEvent
PurchaseEvent CONTAINS SKU
PurchaseEvent OCCURS_AT Touchpoint
PurchaseEvent MOTIVATED_BY NeedState
SKU CONSUMED_IN ConsumptionOccasion
ConsumptionEvent GENERATES Feedback
Feedback EXPRESSES Sentiment
Complaint CONCERNS SKU
Complaint RELATES_TO Batch
LoyaltyBehavior FOLLOWS PurchaseEvent
SwitchingEvent MOVES_FROM Brand
SwitchingEvent MOVES_TO Brand
```

### Stage 11: Returns, waste and circularity

**Purpose:** Manage product returns, packaging recovery, expiry, waste and downstream sustainability.

**Activities**
- Process consumer or customer return
- Identify damaged or expired product
- Recall affected batch
- Dispose or rework product
- Recover packaging
- Recycle material
- Measure waste
- Trace sustainability impact
- Implement corrective action

**Outputs**
- Return disposition
- Product recall
- Disposal event
- Recycled material
- Waste measure
- Sustainability outcome
- Corrective action

**Relationships**
```
Return REFERENCES SKU
Return REFERENCES Batch
ProductRecall AFFECTS Batch
ProductRecall INITIATED_BY QualityIssue
Disposition DETERMINES ReturnOutcome
Waste GENERATED_BY Batch
Waste TREATED_BY DisposalMethod
PackagingMaterial RECOVERED_THROUGH RecoveryProgram
RecycledMaterial REPLACES PackagingMaterial
CorrectiveAction ADDRESSES RootCause
```

## 5. How subsequent layers enrich the value-chain spine

The architectural principle should be:

```
Value-chain node first
→ attach process
→ attach business object
→ attach participant/channel
→ attach metric/risk
→ attach consumer signal
```

### Example: promotion effectiveness

**Layer 1**
```
Customer, Channel and Revenue Growth
→ Retail and Outlet Execution
→ Purchase and Consumption
```

**Layer 2: functional process**
```
Trade Promotion Management
Campaign-to-Conversion
Order-to-Cash
Finance and Performance
```

**Layer 3: product**
```
Brand
Category
SKU
PackPricePoint
```

**Layer 4: ecosystem**
```
Distributor
Retailer
Outlet
Marketplace
MicroMarket
```

**Layer 5: performance**
```
PrimarySales
SecondarySales
SellOut
PromotionSpend
IncrementalVolume
GrossToNet
PromotionROI
Margin
```

**Layer 6: consumer**
```
ConsumerSegment
NeedState
PurchaseOccasion
Basket
RepeatPurchase
SwitchingSignal
```

The graph can then answer:

> Which trade promotions generated distributor loading but failed to produce outlet-level sell-through or repeat consumer purchase?

That query cannot be answered by a document-only RAG implementation. The graph must traverse:

```
TradePromotion
→ CustomerOrder
→ DistributorInventory
→ OutletAvailability
→ SellOutTransaction
→ PurchaseEvent
→ RepeatPurchase
→ PromotionSpend
→ Margin
```

## 6. Recommended sequence of builds

### Build 1: Value-chain foundation
Create:
- 11 value-chain-stage nodes
- Approximately 60–80 value-chain activities
- Trigger, input, output and decision nodes
- PRECEDES, CONSUMES, PRODUCES and DEPENDS_ON relationships
- Source-document citations

What the SLM can do: explain how the CPG business operates and locate prior knowledge by value-chain stage.

### Build 2: Functional-process overlay
Map L2 and L3 processes to each value-chain activity.

Example:
```
ValueChainStage: Manufacturing
    ENABLED_BY Process: Plan-to-Produce
    ENABLED_BY Process: Quality-to-Release
    ENABLED_BY Process: Maintain-to-Operate
    ENABLED_BY Process: Record-to-Report
```

The Finance ontology already developed can be connected here rather than rebuilt independently. For example, trade promotion accrual, claim settlement, product costing, inventory provisioning and profitability connect to multiple CPG value-chain stages. Consumer_Markets_Finance_Ontology_L3 1.xlsx treats these L3 processes as endpoints with events, outputs, KPIs, risks and controls. [Consumer_M..._L3 1.xlsx | Outlook]

### Build 3: Product master and traceability
Add:
- Brand/category/product hierarchy
- Formulation and ingredient graph
- Packaging hierarchy
- SKU and pack-price structure
- Batch and lot traceability
- Quality specifications and claims

What the SLM can do: connect consumer need to formulation, ingredient, batch, quality and commercial outcome.

### Build 4: Ecosystem and channel graph
Add:
- Suppliers
- Plants and co-packers
- Warehouses
- Distributors
- Retailers and outlets
- E-commerce and quick-commerce nodes
- Geographic and micro-market hierarchy

What the SLM can do: reason across participants and markets rather than only retrieve product documents.

### Build 5: KPI, risk and decision graph
Add:
- Metric definitions
- Actuals, targets and benchmarks
- Risks and controls
- Drivers and causal hypotheses
- Decision records
- Management actions

What the SLM can do: explain performance, identify evidence and suggest areas for investigation.

### Build 6: Consumer intelligence graph
Add:
- Segments and need states
- Purchase and consumption occasions
- Journey and touchpoints
- Feedback and complaints
- Loyalty and switching
- External market signals

What the SLM can do: link operational performance to consumer behaviour and demand.

## 7. MVP boundary

The initial MVP should not attempt all 11 stages at equal depth. Start with one connected commercial thread:

```
Consumer insight
→ demand forecast
→ SKU and pack
→ distributor
→ outlet
→ promotion
→ availability
→ sell-out
→ margin
→ consumer response
```

### Priority value-chain stages for the MVP
- Consumer and market insight
- Demand, supply and inventory planning
- Customer, channel and revenue growth
- Retail and outlet execution
- Purchase, consumption and feedback

### Priority entities
```
Brand
Category
SKU
PackPricePoint
ConsumerSegment
NeedState
Geography
MicroMarket
Channel
Distributor
Retailer
Outlet
DemandForecast
InventoryPosition
TradePromotion
CustomerOrder
AvailabilityObservation
SellOutTransaction
PurchaseEvent
PromotionSpend
Margin
KPI
SourceEvidence
```

### Priority relationships
```
BELONGS_TO
TARGETS
APPLIES_TO
FORECASTS
STOCKS
LOCATED_IN
SERVED_BY
OFFERS
PLACED_BY
FULFILLS
OBSERVED_AT
MEASURES
OCCURS_AT
GENERATES
REDUCES
IMPACTS
DERIVED_FROM
SUPPORTED_BY_EVIDENCE
```

This bounded start is important because the previous platform assessment found cases where nodes were generated without the relationships required for connected queries. The first acceptance criterion should therefore be successful multi-hop retrieval, not the raw number of nodes. [RE: Micro-...Next Steps | Outlook]

## 8. Changes I would make to the slide

**Title**
CPG intelligence grows from a connected value-chain spine into six reasoning layers

**Subtitle**
Each layer enriches the same knowledge graph, enabling the SLM to move from understanding how the sector operates to explaining performance and consumer behaviour.

**Replace Layer 1 text with**
- Consumer and market insight
- Portfolio and category strategy
- Product innovation and formulation
- Ingredients and packaging sourcing
- Manufacturing, quality and packaging
- Demand and supply planning
- Distribution and fulfilment
- Channel and retail execution
- Purchase, consumption and circularity

**Replace centre label**
Instead of "Consumer KG", use "CPG Intelligence Graph".

**Revised enrichment logic**
```
Sector value flow
→ operating processes
→ product and traceability
→ ecosystem and route-to-market
→ performance, risk and decisions
→ consumer behaviour and experience
```

The story should be that the programme is building one evolving CPG intelligence graph, not adding six repositories. The existing internal materials already articulate this "one ontology, one connected graph" principle. [Consumer_D...nce_Layers | PowerPoint], [Consumer_D...lar_Arcs 1 | PowerPoint], [Consumer_D...n_Layers 1 | PowerPoint]
