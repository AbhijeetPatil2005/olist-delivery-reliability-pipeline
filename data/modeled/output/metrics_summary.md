# Olist Delivery Reliability — Metrics Summary
**Generated:** 2026-09-25 10:19:50
---
## Executive Summary
- **Total Valid Orders Analyzed:** 96,438
- **On-Time Delivery Rate:** 91.88%
- **Average Delay (Late Orders):** 8.87 days
- **States with <50% On-Time:** 0 states < 50%
---
## Detailed Metrics
### On-Time Delivery Rate
- **Value:** `91.88%`
- **Stakeholder:** Leadership
- **Notes:** Excludes orders with delivery_status_unclear (missing/invalid timestamps)
- **For Decision:** Headline KPI for monthly reporting and carrier SLA negotiation

### Average Delay (Late Orders Only)
- **Value:** `8.87 days`
- **Stakeholder:** Operations
- **Notes:** Calculated as (actual_delivery - estimated_delivery) for orders where actual > estimated
- **For Decision:** Shows magnitude of delay for the minority of orders that miss their deadline

### Delivery Reliability by State
- **Value:** `27 states analyzed`
- **Stakeholder:** Operations
- **Notes:** Worst state: AL (76.1%)
- **For Decision:** Identifies geographic areas needing carrier or logistics improvements

### Review Score Correlation with Lateness
- **Value:** `On-time: 4.29, Late: 2.57, Delta: -1.73`
- **Stakeholder:** Customer Experience
- **Notes:** Delta of -1.73 shows impact of late delivery on satisfaction
- **For Decision:** Quantifies customer experience impact of delivery reliability

### Delay Split (Pre-Ship vs. In-Transit)
- **Value:** `Pre-ship: 2.35d (20.9%), In-transit: 8.88d (79.1%)`
- **Stakeholder:** Operations
- **Notes:** Pre-ship: order_approved_at -> order_delivered_carrier_date (ops responsibility)
- **For Decision:** Identifies whether to focus improvements on internal processes or carrier relationships

---
## State-by-State Performance
| State | Orders | On-Time Rate | Avg Delay | Pre-Ship | In-Transit |
|-------|--------|--------------|-----------|----------|------------|
| AL | 397 | 76.1% | 2.0d | 2.5d | 20.6d |
| MA | 716 | 80.3% | 1.8d | 2.6d | 17.6d |
| PI | 476 | 84.0% | 1.9d | 2.3d | 15.8d |
| CE | 1,278 | 84.7% | 2.1d | 2.4d | 17.5d |
| SE | 335 | 84.8% | 2.5d | 2.7d | 17.5d |
| BA | 3,256 | 86.0% | 1.5d | 2.4d | 15.6d |
| RJ | 12,350 | 86.5% | 1.6d | 2.5d | 11.6d |
| TO | 274 | 87.2% | 0.6d | 2.4d | 13.8d |
| PA | 946 | 87.6% | 1.4d | 2.5d | 19.8d |
| ES | 1,995 | 87.8% | 1.2d | 2.5d | 12.0d |

*Top 10 worst-performing states. Full data in `data/modeled/intermediate/state_aggregations.csv`*
---
## Methodology Notes
1. Orders with missing or impossible delivery timestamps are excluded from KPI calculations
2. Holidays are logged as context but do not reclassify on-time status
3. All calculations use pandas with explicit, reproducible transformations
