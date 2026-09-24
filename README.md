# Olist Delivery Reliability Pipeline

## Business Problem

**Core Question:** Is Olist delivering orders on time, and where in the order lifecycle does delay or failure accumulate?

**Key Performance Indicator (KPI):** Delivery Reliability — specifically, the on-time delivery rate and the breakdown of where delays occur (pre-ship vs. in-transit).

## Stakeholders & Decisions Supported

| Stakeholder | Question They Need Answered | Decision Supported |
|-------------|----------------------------|-------------------|
| **Operations Lead** | Where do delays originate — before carrier handoff or in transit? | Resource allocation between internal ops and carrier relationships |
| **Customer Experience Lead** | Does delivery lateness hurt review scores? | Prioritizing delivery improvements for CS impact |
| **Leadership** | What is the monthly on-time delivery rate we can trust? | Executive reporting, SLA negotiation with carriers |

## Source Overview

This pipeline integrates **10 data sources**:

1. **Olist E-Commerce Dataset (9 tables)** — Orders, items, payments, reviews, products, sellers, customers, geolocation, and category translations from Kaggle.
2. **Brasil API /Feriados** — Brazilian national holidays for delivery context (via API).

For full documentation, see: [docs/source_map.md](docs/source_map.md)

For data relationships and event workflow, see: [docs/workflow_diagram.md](docs/workflow_diagram.md)

## Delivery Status Rules (FDE Judgment Calls)

This pipeline makes explicit, defensible choices about ambiguous data:

| Situation | Treatment | Rationale |
|-----------|-----------|-----------|
| Missing `delivered_customer_date` | **Exclude** from on-time rate | Refusing to guess on ~X% of orders rather than silently inflate/deflate the KPI |
| `delivered` < `shipped` (impossible timeline) | **Flag** as `delivery_timeline_impossible`, exclude | Cannot compute meaningful delay on impossible data |
| Holiday within 3 days of delivery | **Log as context**, do NOT reclassify on-time status | An arbitrary grace period (±3 days) can't be defended without carrier close-day data |

For full documentation of validation rules and data quality findings, see: [docs/known_issues.md](docs/known_issues.md)

## Pipeline Output

### Evidence Table Location

Final metrics are written to:
```
data/modeled/output/metrics_evidence_table.csv
data/modeled/output/metrics_summary.md
```

### Metrics Computed

| Metric | Definition | Stakeholder |
|--------|------------|-------------|
| On-Time Delivery Rate | % of orders delivered by estimated date | Leadership |
| Average Delay (Late Orders) | Mean days late for late orders | Operations |
| Delivery Reliability by State | On-time rate segmented by customer state | Operations |
| Review Score vs. Lateness | Mean review score: on-time vs. late | Customer Experience |
| Delay Split (Pre-Ship vs. In-Transit) | Where does delay accumulate? | Operations |

## Quick Start

### Prerequisites

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Setup

1. **Download Olist Dataset** from Kaggle: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
2. **Place CSV files** in `data/raw/olist/`:
   - `olist_orders_dataset.csv`
   - `olist_order_items_dataset.csv`
   - `olist_order_payments_dataset.csv`
   - `olist_order_reviews_dataset.csv`
   - `olist_products_dataset.csv`
   - `olist_sellers_dataset.csv`
   - `olist_customers_dataset.csv`
   - `olist_geolocation_dataset.csv`
   - `product_category_name_translation.csv`

3. **Run the pipeline:**
   ```bash
   python run_pipeline.py
   ```

### Output

- **Logs:** `logs/pipeline_{timestamp}.log`
- **Metrics:** `data/modeled/output/metrics_evidence_table.csv`
- **Summary:** `data/modeled/output/metrics_summary.md`

## Reproducibility

- The pipeline is **idempotent**: running it again on the same raw data produces the same output.
- Output directories are cleaned at the start of each run.
- Checksums are validated at ingest to ensure raw data hasn't changed.

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| Missing raw files | Pipeline fails loudly with list of expected files |
| API failure (holidays) | Retries 3x, then fails with diagnostic |
| Malformed rows | Logged and skipped, pipeline continues |
| Zero orders after validation | Check raw data quality, review `logs/` |

## Project Structure

```
├── data/
│   ├── raw/
│   │   ├── olist/           # Original Olist CSVs (untouched)
│   │   └── feriados/        # API-retrieved holidays
│   ├── validated/           # Flagged/cleaned intermediate files
│   └── modeled/
│       └── output/          # Final metrics evidence table
├── src/
│   ├── ingest.py            # CSV + API retrieval
│   ├── validate.py          # Profiling + validation rules
│   ├── transform_model.py   # Workflow modeling
│   └── metrics.py           # Metric computation
├── docs/
│   ├── source_map.md        # Table documentation
│   ├── workflow_diagram.md  # Mermaid ER/workflow diagram
│   └── known_issues.md      # Data quality findings
├── logs/                    # Pipeline execution logs
├── run_pipeline.py          # Single entry point
├── requirements.txt
└── README.md
```