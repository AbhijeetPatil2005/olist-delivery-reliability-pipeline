# Requirements: FDE Data Foundations — Olist Delivery Reliability Pipeline

## Business Problem

**Core Question:** Is the Olist e-commerce platform delivering orders on time, and where in the order lifecycle does delay or failure accumulate?

**KPI:** Delivery Reliability — tracking on-time delivery rates, delay magnitudes, and the correlation between delivery performance and customer satisfaction.

## Stakeholders & Decisions

| Stakeholder | Question They Need Answered | Decision Supported |
|-------------|----------------------------|-------------------|
| **Operations Lead** | Where do delays originate — before carrier handoff or in transit? | Resource allocation between internal ops and carrier relationships |
| **Customer Experience Lead** | Does delivery lateness hurt review scores? | Prioritizing delivery improvements for CS impact |
| **Leadership** | What is the monthly on-time delivery rate we can trust? | Executive reporting, SLA negotiation with carriers |

## Data Sources

### Primary: Olist Brazilian E-Commerce Dataset (Kaggle)

| Source Table | Business Purpose | Owning System | Grain (1 row =) | Key Fields | Known Gaps |
|-------------|------------------|---------------|-----------------|------------|------------|
| `orders` | Core order lifecycle | Order Management | One order | `order_id`, `customer_id`, `order_status`, `order_purchase_timestamp`, `order_approved_at`, `order_delivered_carrier_date`, `order_delivered_customer_date`, `order_estimated_delivery_date` | No carrier tracking, no live GPS |
| `order_items` | Line items per order | Order Management | One item per order line | `order_id`, `product_id`, `seller_id`, `price`, `freight_value` | No item-level delivery tracking |
| `order_payments` | Payment details | Billing System | One installment per payment | `order_id`, `payment_sequential`, `payment_type`, `payment_value` | Payment timing may not match order events |
| `order_reviews` | Customer feedback | Feedback System | One review per order | `review_id`, `order_id`, `review_score`, `review_creation_date`, `review_answer_timestamp` | Reviews optional; timing independent of delivery |
| `products` | Product catalog | Catalog System | One product | `product_id`, `category_name`, `product_weight_g`, `product_length_cm`, etc. | Product attributes vary in completeness |
| `product_category_name_translation` | Category translation | Catalog System | One category | `product_category_name`, `product_category_name_english` | English translation only |
| `sellers` | Seller registry | Marketplace System | One seller | `seller_id`, `seller_zip_code_prefix`, `seller_city`, `seller_state` | No performance metrics attached |
| `customers` | Customer registry | CRM/Logistics | One customer | `customer_id`, `customer_zip_code_prefix`, `customer_city`, `customer_state` | No PII beyond location |
| `geolocation` | ZIP prefix geography | Logistics/Geo Ref | One ZIP prefix | `geolocation_zip_code_prefix`, `geolocation_lat`, `geolocation_lng`, `geolocation_city`, `geolocation_state` | Coarse geography; some ZIPs missing |

### Secondary: Brazilian Holidays API

**Chosen API:** Brasil API (`https://brasilapi.com.br/docs/api/ebit`) — specifically the `/feriados/v1/{year}` endpoint for retrieving Brazilian national holidays.

**Rationale:** Holidays directly impact delivery time expectations and performance metrics. An order shipped one day before a holiday weekend may legitimately be delayed compared to business-day shipping estimates.

**Design Decision (approved):** Holidays are logged as context columns (e.g., `holiday_within_3_days`) but do NOT reclassify an order's on-time status. This keeps the on-time metric honest — no "silent reclassification" with arbitrary grace periods that can't be defended with data.

## Success Criteria by Grading Dimension

### 1. Source Reasoning (20%)
- [ ] Source map markdown documenting all tables (purpose, system, grain, key fields, gaps)
- [ ] Mermaid diagram showing table relationships
- [ ] Explicit mapping table: Business question → Source table(s) required

### 2. Retrieval (20%)
- [ ] Raw Olist CSV files in `data/raw/olist/` (7+ files)
- [ ] Brazilian holidays API data cached to `data/raw/feriados/`
- [ ] Completeness check logs (expected vs. actual row counts, checksums)
- [ ] No raw files overwritten in place

### 3. Profiling & Validation (20%)
- [ ] Profile report per table: nulls, duplicates, value ranges, referential integrity
- [ ] Documented validation rules with business rationale
- [ ] Known/Unknown/Assumptions/Limitations document
- [ ] Bad records flagged, counted, and logged — never silently dropped

### 4. Workflow Modeling + Metrics (20%)
- [ ] Entity-Event-Outcome model documented
- [ ] At least 3 delivery-reliability metrics computed:
  - On-time delivery rate
  - Average delay for late deliveries
  - Delivery reliability by state
- [ ] Metrics mapped to stakeholder questions
- [ ] Evidence table output (CSV + markdown summary)

### 5. Pipeline Dependability (20%)
- [ ] Single entry point: `python run_pipeline.py`
- [ ] Logging at each stage (rows in, flagged, out) → log file
- [ ] Idempotent: rerun produces same output
- [ ] Error handling: missing files, malformed data, API failures fail loudly
- [ ] Evidence table in `data/modeled/output/`

## Deliverables Checklist

```
/data/raw/olist/           # Original Olist CSVs (untouched)
/data/raw/feriados/        # API-retrieved holidays
/data/validated/           # Flagged/cleaned intermediate files
/data/modeled/output/      # Final metrics evidence table
/src/ingest.py             # CSV + API retrieval module
/src/validate.py           # Profiling + validation rules
/src/transform_model.py    # Workflow modeling
/src/metrics.py            # Metric computation
/run_pipeline.py           # Single entry point
/docs/source_map.md        # Table documentation
/docs/workflow_diagram.md  # Mermaid ER/workflow diagram
/docs/known_issues.md      # Data quality findings & assumptions
/README.md                 # Project overview & run instructions
```

## Decisions Pending User Input

1. **API Strictness:** Should holidays within ±3 days of estimated delivery date be considered as "explanation for delay" (not flagged as late), or should we flag them and let analysts interpret?
2. **Validation Rigor:** Should orders with missing `delivered_customer_date` be excluded entirely, or should we differentiate between "shipped but not delivered" (still in transit) vs "status unclear"?
3. **Demo Judgment Call:** Which single judgment call should the demo highlight? (Options: Holiday handling logic, ambiguous delivery-status treatment, payment-order value mismatch approach)