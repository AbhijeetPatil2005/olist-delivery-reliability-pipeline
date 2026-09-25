# Design: FDE Data Foundations — Olist Delivery Reliability Pipeline

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    run_pipeline.py (entry point)                 │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         STAGE 1: INGEST                          │
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │  Olist CSV Files │    │  Brasil API     │                     │
│  │  (7+ tables)     │    │  /feriados      │                     │
│  └────────┬────────┘    └────────┬────────┘                     │
│           │                      │                               │
│           └──────────────────────┼──────────────────────────────┘
│                                  ▼                               │
│                        data/raw/ (immutable)                     │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      STAGE 2: VALIDATE                           │
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │  Profile Tables │    │  Apply Rules    │                     │
│  │  (nulls, dups,  │    │  (referential,  │                     │
│  │   ranges)        │    │   business)     │                     │
│  └────────┬────────┘    └────────┬────────┘                     │
│           │                      │                               │
│           └──────────────────────┼──────────────────────────────┘
│                                  ▼                               │
│                    data/validated/ (flagged, cleaned)            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   STAGE 3: TRANSFORM_MODEL                       │
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │  Event Sequence │    │  Entity-Event   │                     │
│  │  Reconstruction │    │  Model Tables   │                     │
│  └────────┬────────┘    └────────┬────────┘                     │
│           │                      │                               │
│           └──────────────────────┼──────────────────────────────┘
│                                  ▼                               │
│                      data/modeled/intermediate/                  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       STAGE 4: METRICS                           │
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │  KPI Computations│    │  Evidence Table │                     │
│  │  (5 metrics)    │    │  (CSV + Markdown│                     │
│  └─────────────────┘    └─────────────────┘                     │
│                                  │                               │
│                                  ▼                               │
│                          data/modeled/output/                    │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow (Source → Target)

### Ingest Layer

| Source | Destination | Mode |
|--------|-------------|------|
| `olist_orders_dataset.csv` | `data/raw/olist/orders.csv` | CSV download |
| `olist_order_items_dataset.csv` | `data/raw/olist/order_items.csv` | CSV download |
| `olist_order_payments_dataset.csv` | `data/raw/olist/order_payments.csv` | CSV download |
| `olist_order_reviews_dataset.csv` | `data/raw/olist/order_reviews.csv` | CSV download |
| `olist_products_dataset.csv` | `data/raw/olist/products.csv` | CSV download |
| `olist_sellers_dataset.csv` | `data/raw/olist/sellers.csv` | CSV download |
| `olist_customers_dataset.csv` | `data/raw/olist/customers.csv` | CSV download |
| `olist_geolocation_dataset.csv` | `data/raw/olist/geolocation.csv` | CSV download |
| `product_category_name_translation.csv` | `data/raw/olist/category_translation.csv` | CSV download |
| Holidays API (2023-2026) | `data/raw/feriados/brasil_holidays.json` | HTTP GET |

### Validation Layer

| Input | Output | Transformation |
|-------|--------|----------------|
| `data/raw/olist/*.csv` | `data/validated/orders_validated.csv` | Flag nulls, check date order |
| `data/raw/olist/*.csv` | `data/validated/order_items_validated.csv` | Check FK to orders, positive prices |
| `data/raw/olist/*.csv` | `data/validated/payments_validated.csv` | Check FK, reasonable values |
| `data/raw/olist/*.csv` | `data/validated/reviews_validated.csv` | Check FK, score range 1-5 |
| `data/raw/olist/*.csv` | `data/validated/products_validated.csv` | Check required fields |
| `data/raw/olist/*.csv` | `data/validated/sellers_validated.csv` | Deduplicate by seller_id |
| `data/raw/olist/*.csv` | `data/validated/customers_validated.csv` | Deduplicate by customer_id |
| `data/raw/olist/*.csv` | `data/validated/geolocation_validated.csv` | Check lat/lng ranges |
| `data/raw/feriados/*.json` | `data/validated/holidays_validated.json` | Validate schema |

### Transform/Model Layer

| Output Table | Description | Key Columns |
|--------------|-------------|-------------|
| `orders_enriched.csv` | Orders with delivery outcomes | order_id, status, events (placed, approved, shipped, delivered, reviewed), on_time_flag |
| `order_events.csv` | Flattened event sequence per order | order_id, event_type, timestamp |
| `delivery_metrics.csv` | Aggregated delivery performance | state, on_time_rate, avg_delay_days, total_orders |

### Output Layer

| Output File | Audience | Purpose |
|-------------|----------|---------|
| `metrics_evidence_table.csv` | Leadership/Operations | Trustworthy KPI numbers |
| `metrics_summary.md` | All stakeholders | Readable summary with context |

## Entity-Event Model

### Entities
- **Customer** (`customer_id`, city, state)
- **Seller** (`seller_id`, city, state)
- **Product** (`product_id`, category, attributes)
- **Order** (`order_id`, customer_id, seller_ids[], status)

### Events/States (per order)
1. **placed** — `order_purchase_timestamp`
2. **approved** — `order_approved_at`
3. **shipped** — `order_delivered_carrier_date`
4. **delivered** — `order_delivered_customer_date`
5. **reviewed** — `review_creation_date`

### Outcomes
- **on_time**: delivered_timestamp <= estimated_delivery_date
- **late**: delivered_timestamp > estimated_delivery_date
- **delivery_status_unclear**: missing delivered_timestamp or delivered < shipped
- **review_score**: 1-5 from `order_reviews`

## Metrics Definitions

### Metric 1: On-Time Delivery Rate
**Definition:** Percentage of orders with `delivered_timestamp <= estimated_delivery_date`

**Formula:** `COUNT(order_id WHERE on_time = true) / COUNT(order_id WITH valid delivery) * 100`

**Exclusion Rule:** Orders with `delivery_status_unclear` (missing or impossible timestamps) are excluded from both numerator and denominator — counted separately as "excluded_orders" for transparency.

**Stakeholder:** Leadership (monthly reporting)

### Metric 2: Average Delay (Late Orders Only)
**Definition:** Mean days between `estimated_delivery_date` and `delivered_timestamp` for late orders

**Formula:** `AVG(delivered_timestamp - estimated_delivery_date) WHERE on_time = false`

**Stakeholder:** Operations (identifying systemic delay)

### Metric 3: Delivery Reliability by State
**Definition:** On-time rate segmented by customer state

**Formula:** `GROUP BY customer_state, CALCULATE Metric 1`

**Stakeholder:** Operations (geographic resource allocation)

### Metric 4: Review Score vs. Delivery Lateness
**Definition:** Mean review score for on-time vs. late orders

**Formula:** `AVG(review_score) GROUP BY on_time_flag`

**Stakeholder:** Customer Experience (CS impact analysis)

### Metric 5: Pre-Ship vs. In-Transit Delay Split
**Definition:** Split of total delay into:
- **Order-to-Ship:** `shipped_timestamp - approved_timestamp`
- **In-Transit:** `delivered_timestamp - shipped_timestamp`

**Formula:** Both deltas per order, aggregated

**Stakeholder:** Operations (ops vs. carrier responsibility)

## Validation Rules (Business-Oriented)

| Rule ID | Description | Action if Violated |
|---------|-------------|-------------------|
| VAL-001 | `order_delivered_customer_date >= order_delivered_carrier_date` | Flag: `delivery_timeline_impossible` |
| VAL-002 | `order_delivered_customer_date >= order_purchase_timestamp` | Flag: `delivery_before_purchase` |
| VAL-003 | `order_approved_at >= order_purchase_timestamp` | Flag: `approval_before_purchase` |
| VAL-004 | `review_score` ∈ {1,2,3,4,5} | Flag: `invalid_score` |
| VAL-005 | `payment_value` > 0 | Flag: `invalid_payment` |
| VAL-006 | `order_items.order_id` EXISTS in `orders` | Flag: `orphan_order_item` |
| VAL-007 | `order_reviews.order_id` EXISTS in `orders` | Flag: `orphan_review` |
| VAL-008 | `order_payments.order_id` EXISTS in `orders` | Flag: `orphan_payment` |

## Pipeline Stages (Code Modules)

### Stage 1: Ingest (`src/ingest.py`)
- Functions: `download_olist_csvs()`, `fetch_brasil_holidays()`, `verify_completeness()`
- Output: Raw files in `data/raw/`
- Logging: Files downloaded, row counts, checksums

### Stage 2: Validate (`src/validate.py`)
- Functions: `profile_table()`, `apply_validation_rules()`, `generate_validation_report()`
- Output: Validated files in `data/validated/`, validation log
- Logging: Null counts, duplicate counts, rule violations per table

### Stage 3: Transform/Model (`src/transform_model.py`)
- Functions: `reconstruct_events()`, `build_entity_tables()`, `calculate_delivery_outcomes()`
- Output: Modeled tables in `data/modeled/`
- Logging: Orders processed, events reconstructed, outcomes assigned

### Stage 4: Metrics (`src/metrics.py`)
- Functions: `compute_metrics()`, `generate_evidence_table()`
- Output: Evidence table in `data/modeled/output/`
- Logging: Metric values computed, table written

### Entry Point (`run_pipeline.py`)
- Orchestrates all stages in order
- Handles errors gracefully
- Produces final summary

## Key Design Decisions (Confirmed)

1. **Processing Engine:** Pandas for simplicity and readability (dataset size ~100K rows; pandas is fine and explainable in demo)

2. **Idempotency Strategy:**
   - Output directories are cleaned at start of each run
   - Timestamped log files preserve run history
   - Checksums validated at ingest to ensure reproducibility

3. **Error Handling Philosophy:**
   - Missing raw file → Fail loudly with clear message
   - Malformed row → Skip row, log count + sample, continue
   - API failure → Retry 3x, then fail with diagnostic

4. **Holiday Handling (DECISION APPROVED — Option A):**
   - Holidays do NOT affect on-time calculation
   - Holidays are logged as context columns (e.g., `days_from_nearest_holiday`)
   - Rationale: An arbitrary grace period (±3 days) can't be defended with carrier data; keeping the metric honest is more valuable than "massaging" results
   - Analysts can still examine holiday proximity post-hoc without quietly changing the KPI definition

5. **Ambiguous Delivery Timestamps (FDE Judgment Call):**
   - Orders with `delivery_status_unclear` (missing or impossible timestamps) are EXCLUDED from on-time rate calculation
   - They are counted and reported separately as "excluded_orders" with clear flag codes
   - This is NOT silently dropped — it's visible and defensible: we refuse to guess on 3.02% of orders rather than inflate/deflate the KPI with assumptions

6. **Demo Focus (approved):** The delivery_status_unclear handling is the primary judgment call to highlight in the 3-5 minute demo — it directly demonstrates the "don't silently fix" principle from the rubric.

## Output Evidence Table Schema

```
metrics_evidence_table.csv:
- metric_name
- metric_value
- numerator
- denominator
- time_period
- stakeholder_notes
```

## File Naming Conventions

| Type | Pattern | Example |
|------|---------|---------|
| Raw Olist | `{table}.csv` | `orders.csv` |
| Raw API | `brasil_holidays_{year}.json` | `brasil_holidays_2024.json` |
| Validated | `{table}_validated.csv` | `orders_validated.csv` |
| Modeled | `{table}.csv` | `orders_enriched.csv` |
| Logs | `pipeline_{timestamp}.log` | `pipeline_20240924_143022.log` |

## Validation Rule Flag Codes

| Flag | Meaning | Implication for Analysis |
|------|---------|-------------------------|
| `delivery_timeline_impossible` | Delivered before shipped | Exclude from delivery timing analysis |
| `delivery_before_purchase` | Delivered before order placed | Exclude from all order analysis |
| `orphan_order_item` | order_id not in orders | FK violation, investigate source |
| `orphan_review` | order_id not in orders | FK violation, investigate source |
| `orphan_payment` | order_id not in orders | FK violation, investigate source |
| `missing_required_field` | Null in required field | May be acceptable (review optional) |