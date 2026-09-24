# Task Breakdown: FDE Data Foundations — Olist Delivery Reliability Pipeline

## Phase 1: Project Setup & Documentation ✅ COMPLETED

### Task 1.1: Create repository structure
- [x] Create directories: `data/raw/olist`, `data/raw/feriados`, `data/validated`, `data/modeled/output`, `src`, `docs`, `logs`
- [x] Initialize `requirements.txt` with pandas, requests, python-dateutil

### Task 1.2: Create source map documentation
- [x] Draft `docs/source_map.md` with all 10 source tables documented
- [x] Include table purpose, owning system, grain, key fields, known gaps
- [x] Add business question → source table mapping table

### Task 1.3: Create workflow diagram
- [x] Draft `docs/workflow_diagram.md` with Mermaid ER diagram
- [x] Show relationships: orders → order_items → sellers, orders → payments, orders → reviews, customers ↔ geolocation

### Task 1.4: Create README
- [x] Draft `README.md` with business problem, KPI, stakeholders, source overview, setup/run instructions, evidence table location

## Phase 2: Ingestion (Retrieval) ✅ COMPLETED

### Task 2.1: Create ingest module structure
- [x] Create `src/ingest.py` with main functions:
  - `download_olist_files()`
  - `fetch_brasil_holidays()`
  - `verify_raw_completeness()`
  - `log_ingestion_stats()`

### Task 2.2: Implement Olist CSV download
- [x] Note: User must provide Kaggle files — create placeholder/download stub
- [x] Create expected file manifest (files → expected row counts)
- [x] Implement checksum verification (SHA256 or row count)

### Task 2.3: Implement Brazil Holidays API retrieval
- [x] Use Brasil API: `https://brasilapi.com.br/api/feriados/v1/{year}`
- [x] Fetch years 2023-2026 (covering order date range)
- [x] Cache to `data/raw/feriados/brasil_holidays_{year}.json`

### Task 2.4: Create completeness verification
- [x] Define expected files + row counts for Olist tables
- [x] Generate ingestion log with file existence, row count, checksum
- [x] Fail if expected files missing or checksums don't match

## Phase 3: Profiling & Validation ✅ COMPLETED (code written)

### Task 3.1: Create validation module structure
- [x] Create `src/validate.py` with main functions:
  - `profile_table()`
  - `apply_validation_rules()`
  - `generate_validation_report()`

### Task 3.2: Implement table profiling
- [x] For each table: count rows, nulls per column, duplicates per key, value ranges for numeric/date fields
- [x] Profile output: structured dict with all stats

### Task 3.3: Implement validation rules
- [x] Code each rule from design.md (VAL-001 through VAL-008)
- [x] Each rule returns flag code and row indices

### Task 3.4: Generate validation output
- [x] Write flagged rows to `data/validated/orders_validated.csv` + `orders_excluded.csv`
- [x] Generate `data/validated/validation_summary.json` with counts per flag
- [ ] Generate `docs/known_issues.md` documenting findings → **REMAINING**

## Phase 4: Workflow Modeling ✅ COMPLETED (code written)

### Task 4.1: Create transform module structure
- [x] Create `src/transform_model.py` with main functions:
  - `reconstruct_event_sequence()`
  - `enrich_orders_with_outcomes()`
  - `build_entity_tables()`

### Task 4.2: Implement event reconstruction
- [x] For each order, extract timestamps for: placed, approved, shipped, delivered, reviewed
- [x] Create `data/modeled/intermediate/order_events.csv` with event_type, timestamp per order

### Task 4.3: Implement delivery outcome assignment
- [x] For each order with valid delivery:
  - on_time = delivered <= estimated
  - delay_days = delivered - estimated (if late)
  - delivery_status_unclear if missing/invalid timestamp

### Task 4.4: Build state/region aggregations
- [x] Join orders → customers → geolocation for state mapping
- [x] Prepare grouped data for metrics by state

## Phase 5: Metrics Computation ✅ COMPLETED (code written)

### Task 5.1: Create metrics module structure
- [x] Create `src/metrics.py` with main functions:
  - `compute_on_time_rate()`
  - `compute_avg_delay()`
  - `compute_delivery_by_state()`
  - `compute_review_correlation()`
  - `compute_delay_split()`
  - `generate_evidence_table()`

### Task 5.2: Implement Metric 1 (On-Time Rate)
- [x] Calculate: count(on_time) / count(valid_delivery) * 100
- [x] Store numerator, denominator for auditability

### Task 5.3: Implement Metric 2 (Avg Delay)
- [x] Calculate mean delay for late orders only
- [x] Express in days (round to 2 decimals)

### Task 5.4: Implement Metric 3 (By State)
- [x] Group by customer_state
- [x] Calculate on-time rate per state
- [x] Sort by worst performance

### Task 5.5: Implement Metric 4 (Review Correlation)
- [x] Join orders → reviews
- [x] Calculate mean review_score for on_time vs late groups
- [x] Compute delta (late - on_time) to show impact

### Task 5.6: Implement Metric 5 (Delay Split)
- [x] Calculate order_to_ship = shipped - approved
- [x] Calculate in_transit = delivered - shipped
- [x] Report mean split

### Task 5.7: Generate evidence table
- [x] Create `data/modeled/output/metrics_evidence_table.csv`
- [x] Columns: metric_name, value, numerator, denominator, notes, stakeholder
- [x] Create `data/modeled/output/metrics_summary.md` for non-technical readers

## Phase 6: Pipeline Orchestration ✅ COMPLETED

### Task 6.1: Create entry point
- [x] Create `run_pipeline.py`
- [x] Import and call each stage in order
- [x] Handle keyboard interrupt gracefully

### Task 6.2: Implement logging
- [x] Configure logging to file (`logs/pipeline_{timestamp}.log`)
- [x] Log at each stage: stage start, rows in, rows processed, rows out, stage complete
- [x] Log validation flags and counts

### Task 6.3: Implement error handling
- [x] Try/except around each stage
- [x] Missing raw file → clear error message
- [x] Malformed data → log and continue with count
- [x] API failure → retry 3x, then fail

### Task 6.4: Make idempotent
- [x] Clean output directories at start of run
- [x] Validate checksums before processing
- [x] Same input → same output (deterministic)

## Phase 7: Final Documentation & Polish ✅ COMPLETED

### Task 7.1: Review and refine source_map.md
- [x] Ensure all 10 tables documented with business purpose
- [x] Add explicit business question → source mapping

### Task 7.2: Finalize known_issues.md
- [x] Document all validation findings
- [x] Add section for Assumptions and Limitations
- [x] Add section for Unknowns (questions for further investigation)

### Task 7.3: Test end-to-end
- [ ] Awaiting Olist data files — pipeline ready to run

### Task 7.4: Prepare demo script outline
- [x] Draft 3-5 minute demo script
- [x] Highlight one significant judgment call (recommend: holiday handling or delivery_status_unclear logic)
- [x] Create talking points for each stakeholder's question

## Task Dependencies

```
Phase 1 (Setup) ──────► Phase 2 (Ingest) ──────► Phase 3 (Validate)
       │                      │                        │
       │                      │                        │
       ▼                      ▼                        ▼
Task 1.2, 1.3           Task 2.4                  Task 3.4
(source map)            (completeness)            (known_issues)

                                                       │
                                                       ▼
Phase 5 (Metrics) ◄────── Phase 4 (Transform) ◄───── Phase 3 (Validate)
       │                       │                       (model output)
       │                       │                            │
       │                       ▼                            │
       └───────────────── Task 4.3                         │
       (needs modeled data   (order_events)               │
        to compute metrics)                                │
                                                         ▼
                                               All validation complete
                                                         │
                                                         ▼
Phase 6 (Orchestrate) ──────► Phase 7 (Polish) ──────► DONE
       │                              │
       │                              ▼
       └────────────────────── Demo script ready
       (run_pipeline.py)
```

## Estimation (Optional)

| Phase | Estimated Time | Priority |
|-------|---------------|----------|
| Phase 1: Setup | 30 min | High |
| Phase 2: Ingest | 45 min | High |
| Phase 3: Validate | 60 min | High |
| Phase 4: Transform | 45 min | Medium |
| Phase 5: Metrics | 45 min | Medium |
| Phase 6: Orchestrate | 30 min | High |
| Phase 7: Polish | 30 min | Medium |

**Total estimated time:** ~5 hours (can be done in sections)