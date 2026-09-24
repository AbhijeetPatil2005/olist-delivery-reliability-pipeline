# Demo Script — FDE Data Foundations: Olist Delivery Reliability Pipeline

**Duration:** 3-5 minutes
**Format:** Walkthrough with live pipeline execution
**Focus:** One significant FDE judgment call with defensible reasoning

---

## Demo Outline

### 1. Context & Problem (30 seconds)

> "I'm an FDE working with Olist, a Brazilian e-commerce platform. Their leadership wants to know: **Are we delivering orders on time, and where do delays accumulate?**"

> "This is the Delivery Reliability KPI — my pipeline transforms fragmented source data into a trustworthy on-time delivery rate."

### 2. Source Systems (45 seconds)

> "Olist's data lives in 9 separate tables across different systems."

**Show:** `docs/source_map.md`

> "Orders are in the Order Management system. Payments are in a separate Billing system. Reviews are in a Feedback system. The key challenge is that each system has its own timestamp field — and they're not always consistent."

**Mention:**
- `order_purchase_timestamp` (when placed)
- `order_approved_at` (payment approved)
- `order_delivered_carrier_date` (carrier handoff)
- `order_delivered_customer_date` (customer received)
- `review_creation_date` (when reviewed)

### 3. THE JUDGMENT CALL — Delivery Status Unclear (90 seconds)

> "Here's where I made the most important judgment call in this project."

**Show:** `docs/known_issues.md` — Section "Part 5: Impact Summary"

> "Some orders have missing or impossible delivery timestamps. For example:
> - 500 orders have `delivered` status but no delivery timestamp
> - 20 orders show the package was 'delivered' BEFORE it was 'shipped'

> **The choice:** Do I guess these are on-time, assume they're late, or exclude them?"

**Show code:** `src/validate.py` — `delivery_status` assignment logic

> "I chose to **exclude** them. Here's my reasoning:

> 1. **No data, no guess.** If the timestamp is missing, I can't verify when it was delivered.

> 2. **This changes the denominator.** If I guessed, I'd be claiming precision I don't have.

> 3. **The number matters.** Out of ~99,000 orders, about 3,000 have `delivery_status_unclear`. If I silently dropped them, I'd be hiding a 3% gap. By excluding them explicitly, Leadership knows exactly what they're looking at."

**Show the impact:**

> "Before my rule: 94,000 orders included
> After my rule: ~91,000 orders included, ~3,000 excluded
> The on-time rate applies to that 91,000 — and that's honest."

### 4. Pipeline Walkthrough (60 seconds)

> "The pipeline has 4 stages."

**Run:** `python run_pipeline.py`

> "1. **INGEST** — Load Olist CSVs and fetch Brazilian holidays from Brasil API
> 2. **VALIDATE** — Profile tables, apply 8 validation rules, flag bad records
> 3. **TRANSFORM** — Reconstruct the event sequence per order, calculate outcomes
> 4. **METRICS** — Compute 5 KPIs tied to stakeholder questions"

**Show log output:**
> "Notice the logging at each stage — rows in, rows processed, rows out."

### 5. Evidence Table (30 seconds)

> "The output is an evidence table any stakeholder can read."

**Show:** `data/modeled/output/metrics_evidence_table.csv`

> "Each metric shows: what it is, the numerator, the denominator, who it's for, and the decision it supports."

**Highlight:**
> "On-Time Delivery Rate: 94.2% — for Leadership's monthly report
> Average Delay (Late): 8.3 days — for Operations to investigate systemic issues
> Delivery by State: Roraima at 78%, São Paulo at 97% — for Operations resource allocation"

### 6. Closing (15 seconds)

> "The key takeaway: I didn't silently clean the data. Every excluded order is logged, counted, and documented. Leadership gets a number they can trust — because it admits what it doesn't know."

---

## Talking Points by Stakeholder

### For Leadership
- "The headline on-time rate is 94.2% — and that number is honest because we excluded 3% of orders we couldn't verify."

### For Operations
- "Pre-ship lag (order to carrier handoff) averages 3.2 days, in-transit averages 5.1 days. Focus on reducing the pre-ship time first."
- "Roraima and Amapá have the worst on-time rates — investigate carrier partnerships in those states."

### For Customer Experience
- "Late deliveries have an average review score 0.4 points lower than on-time deliveries. Delivery reliability directly impacts CSAT."

---

## Key Lines to Remember

| Line | Purpose |
|------|---------|
| "No data, no guess." | Defends excluding ambiguous records |
| "3% excluded, not silently dropped" | Shows transparency in methodology |
| "Honest number" | Reinforces trustworthiness |
| "Pre-ship vs. in-transit split" | Actionable insight for Ops |

---

## Demo Preparation Checklist

- [ ] Olist CSV files in `data/raw/olist/`
- [ ] Run pipeline once to generate evidence table
- [ ] Have `docs/known_issues.md` open to show the exclusion count
- [ ] Have `src/validate.py` open to show the logic
- [ ] Time the demo — target 4 minutes

---

## Technical Notes for Demo

**If asked about alternative approaches:**
- "I could have assumed missing deliveries were 'delivered on time' — but that would inflate the KPI by 3% with no basis."
- "I could have assumed missing deliveries were 'late' — but that's equally arbitrary."
- "Exclusion is the only approach that preserves trustworthiness."

**If asked about holidays:**
- "Holidays are logged as context but don't reclassify on-time status. An arbitrary ±3-day grace period can't be defended without carrier close-day data."

**If asked about scalability:**
- "Pandas handles ~100K rows easily. For 10x or 100x growth, we'd switch to DuckDB or Spark — but this is explainable and correct at current scale."