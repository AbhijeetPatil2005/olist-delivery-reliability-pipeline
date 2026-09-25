# Known Issues, Assumptions & Limitations

## Document Overview

This document catalogs data quality issues discovered during profiling, explicit assumptions made during pipeline development, and known limitations of the analysis.

---

## Part 1: Data Quality Issues Found

### Validation Rule Results

| Rule | Description | Count | Impact |
|------|-------------|-------|--------|
| VAL-001 | `delivery_timeline_impossible` — delivered before shipped | 23 | Excluded from KPI |
| VAL-002 | `delivery_before_purchase` — delivered before ordered | 0 | N/A |
| VAL-003 | `approval_before_purchase` — approved before ordered | 0 | N/A |
| VAL-004 | `invalid_review_score` — score not 1-5 | 0 | N/A |
| VAL-005 | `invalid_payment_value` — payment <= 0 | 9 | Flagged, investigate |
| VAL-006 | `orphan_order_item` — order_id not in orders | 0 | FK integrity OK |
| VAL-007 | `orphan_review` — order_id not in orders | 0 | FK integrity OK |
| VAL-008 | `orphan_payment` — order_id not in orders | 0 | FK integrity OK |

### Delivery Status Breakdown

| Status | Count | % of Total | Treatment |
|--------|-------|------------|-----------|
| valid_delivery | 96,438 | 96.98% | Included in KPI |
| delivery_missing | 2,965 | 2.98% | Excluded (no delivery timestamp) |
| delivery_timeline_impossible | 23 | 0.02% | Excluded (impossible timeline) |
| approval_timestamp_missing | 14 | 0.01% | Excluded (can't compute pre-ship) |
| carrier_timestamp_missing | 1 | 0.00% | Excluded (can't compute in-transit) |
| **Total Excluded** | **3,003** | **3.02%** | Logged separately |

---

## Part 2: Assumptions Made

### Business Logic Assumptions

| Assumption | Rationale |
|------------|-----------|
| Orders with `delivery_status != 'valid_delivery'` are excluded from on-time rate | No reliable timestamp = cannot verify delivery time; refusing to guess preserves KPI integrity |
| `order_delivered_customer_date` is ground truth for delivery | Carrier handoff timestamp marks when package left Olist, not customer receipt |
| Holidays logged as context, not KPI adjustment | An arbitrary grace period (±3 days) cannot be defended without carrier close-day data |
| `review_score` of -1 means no review | Reviews are optional; orders without reviews are excluded from review correlation |

### Technical Assumptions

| Assumption | Rationale |
|------------|-----------|
| UTF-8 encoding for all CSV files | Olist dataset uses UTF-8 |
| Date formats are consistent | Olist exports use consistent timestamp format |
| Memory is sufficient for pandas operations | Dataset ~100K rows is well within pandas' comfort zone |
| Brasil API is available | External dependency; pipeline fails loudly if unavailable |

---

## Part 3: Limitations

### Scope Limitations

| Limitation | Impact |
|------------|--------|
| No carrier-level data | Cannot attribute in-transit delay to specific carriers |
| No GPS/live tracking | Cannot verify actual delivery route or timing anomalies |
| No warehouse-to-carrier handoff timestamp | Pre-ship lag includes internal processing + carrier pickup wait |
| No inventory availability data | Cannot distinguish stock delays from fulfillment delays |

### Data Completeness Limitations

| Limitation | Impact |
|------------|--------|
| 2,965 orders (2.98%) missing delivery timestamps | ~3% of orders excluded from on-time calculation |
| 99,224 reviews from 96,438 orders | Not every order has a review |
| Geolocation at ZIP prefix level only | Cannot calculate precise customer-seller distances |
| Only national holidays included | State/municipal holidays may affect delivery expectations |

### Methodological Limitations

| Limitation | Impact |
|------------|--------|
| On-time definition is strict (delivered <= estimated) | No "grace period" for weather, traffic, etc. |
| Holiday proximity is context only | May miss orders near a holiday outside tracking window |
| Timezone not explicitly handled | All timestamps appear to be in Brazil time |

---

## Part 4: Unknowns (Questions for Further Investigation)

1. **Why do 2,965 orders have no delivery timestamp?**
   - Orders still "in transit" at data export time?
   - Data export truncation issue?
   - Orders canceled before delivery?

2. **Why do 23 orders show delivered before shipped?**
   - Data entry error in source systems?
   - Timestamp swapping in ETL pipeline?
   - Timezone handling issue?

3. **Do reviews correlate with actual delivery or perceived delivery?**
   - Some reviews are submitted before delivery (per review_creation_date)
   - This may inflate "late delivery" review scores if customers review before confirming receipt

---

## Part 5: Impact Summary

### Records Excluded from On-Time Rate KPI

| Reason | Count | % of Total |
|--------|-------|------------|
| Missing delivery timestamp | 2,965 | 2.98% |
| Impossible timeline (delivered < shipped) | 23 | 0.02% |
| Missing approval timestamp | 14 | 0.01% |
| Missing carrier timestamp | 1 | 0.00% |
| **Total Excluded** | **3,003** | **3.02%** |

### Impact on Metric Interpretation

- **On-time rate (91.88%)** applies only to 96,438 orders with `valid_delivery` status
- **Review correlation** applies only to orders with reviews (~99K of 96K valid)
- **State analysis** applies to all orders with valid customer state (96,438)
- **Delay split** applies to orders with all three timestamps (~95K)

---

## Pipeline Execution Summary

| Stage | Duration | Status |
|-------|----------|--------|
| INGEST | ~5s | 9/9 files verified, 55 holidays cached |
| VALIDATE | ~8s | 96,438 valid, 3,003 excluded |
| TRANSFORM | ~65s | 385,752 events reconstructed |
| METRICS | ~15s | 5 KPIs computed |

---

## Document Version

- **Generated:** 2026-09-24 (auto-populated from pipeline validation)
- **Pipeline Version:** 1.0.0
- **Data Source:** Olist Brazilian E-Commerce Dataset (Kaggle)
---

## Part 6: Verified Failure Handling

### Tested Failure Scenario: Missing Required Raw File

When `olist_orders_dataset.csv` was temporarily removed to test failure handling, the pipeline failed loudly and clearly:

**Terminal Output:**
```
[X] olist_orders_dataset.csv: MISSING
INGESTION FAILED: One or more sources incomplete or unreachable
VALIDATION FAILED: Could not load all required tables
[X] STAGE VALIDATE FAILED
```

**Behavior Analysis:**
- Stage INGEST detected the missing file immediately during completeness verification
- The error message explicitly identifies which file is missing
- Pipeline exited with non-zero status (exit code 1)
- No silent continuation or corrupted output produced
- Log file records the failure with timestamp and stage

**Conclusion:** The pipeline properly fails loudly when required data is missing, providing clear diagnostic output rather than crashing with an unhelpful traceback or producing garbage output.

---
**Verified:** 2026-09-25 | Test: Removed `olist_orders_dataset.csv`, ran `python run_pipeline.py`
### Tested Failure Scenario: Duplicated Order Item

When a row in olist_order_items_dataset.csv was artificially duplicated to test data integrity handling:

**Behavior Analysis:**
- The pipeline ran to completion successfully without throwing any errors or warnings.
- Final metric outcomes (91.88% on-time) and row counts remained exactly the same as a clean run.

**Conclusion:** The pipeline currently lacks a primary-key uniqueness validation rule for order_items. While this did not corrupt the high-level delivery metrics (which rely on the orders table), it silently accepts duplicate items. This is a known limitation that should be fixed before extending the pipeline to item-level metrics (e.g., item volume or product-specific delays).

---
**Verified:** 2026-09-25 | Test: Duplicated first data row in olist_order_items_dataset.csv, ran python run_pipeline.py
