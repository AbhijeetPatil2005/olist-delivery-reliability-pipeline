[TIME] 0:00
[SAY] I'm building a data pipeline for Olist, a Brazilian e-commerce company.
[SHOW] Open README.md to Business Problem section

[TIME] 0:05
[SAY] Their leadership wants to know one thing: are we delivering orders on time?
[SHOW] README.md - Business Problem section

[TIME] 0:10
[SAY] The KPI is the on-time delivery rate, the percentage of orders arriving by their promised date.
[SHOW] README.md - Stakeholder table

[TIME] 0:17
[SAY] Olist's data is fragmented across nine separate tables in different systems.
[SHOW] Open docs/source_map.md

[TIME] 0:23
[SAY] Orders are in one system, payments in another, reviews in a third.
[SHOW] docs/source_map.md - table list

[TIME] 0:29
[SAY] Each table has its own timestamp fields, and they're not always consistent.
[SHOW] docs/source_map.md - orders table detail

[TIME] 0:36
[SAY] I also pulled Brazilian national holidays from the Brasil API as context.
[SHOW] Open docs/workflow_diagram.md

[TIME] 0:42
[SAY] Holidays can affect delivery expectations, so I logged proximity as context but didn't let it reclassify on-time status.
[SHOW] docs/workflow_diagram.md - API box

[TIME] 0:49
[SAY] This is a classic FDE problem: taking messy multi-source data and turning it into a trustworthy metric.
[SHOW] docs/workflow_diagram.md

[TIME] 0:55
[SAY] Here's where I made the most important judgment call in this project.
[SHOW] Open docs/known_issues.md

[TIME] 1:00
[SAY] About three percent of orders have missing or impossible delivery timestamps.
[SHOW] docs/known_issues.md - Delivery Status Breakdown table

[TIME] 1:06
[SAY] Specifically, two thousand nine hundred sixty-five orders have no delivery timestamp at all.
[SHOW] docs/known_issues.md - "delivery_missing: 2,965" row

[TIME] 1:13
[SAY] Twenty-three orders show the package was delivered before it was even shipped.
[SHOW] docs/known_issues.md - "delivery_timeline_impossible: 23" row

[TIME] 1:19
[SAY] That's impossible — you can't deliver before you ship.
[SHOW] docs/known_issues.md - VAL-001 description

[TIME] 1:25
[SAY] I had three choices for these three thousand and three problematic orders.
[SHOW] docs/known_issues.md - Total Excluded row (3,003)

[TIME] 1:32
[SAY] Choice one: assume they were all on-time and inflate the KPI.
[SHOW] docs/known_issues.md

[TIME] 1:37
[SAY] Choice two: assume they were all late and deflate the KPI.
[SHOW] docs/known_issues.md

[TIME] 1:42
[SAY] Choice three: exclude them, log exactly why, and tell leadership the truth.
[SHOW] docs/known_issues.md

[TIME] 1:48
[SAY] I chose option three. No data, no guess.
[SHOW] src/validate.py - delivery_status assignment logic

[TIME] 1:54
[SAY] Leadership gets an honest ninety-one point eight eight percent on-time rate.
[SHOW] data/modeled/output/metrics_evidence_table.csv - On-Time Delivery Rate row

[TIME] 2:01
[SAY] Not a number I massaged to look better by guessing on three percent of orders.
[SHOW] data/modeled/output/metrics_evidence_table.csv - numerator (88,612) and denominator (96,438)

[TIME] 2:08
[SAY] The excluded orders are logged in data/validated/orders_excluded.csv with reason codes.
[SHOW] Open data/validated/orders_excluded.csv - show first few rows with delivery_status column

[TIME] 2:15
[SAY] Anyone can audit exactly what was left out and why — no silent exclusions.
[SHOW] data/validated/orders_excluded.csv - scroll to show reason codes visible

[TIME] 2:23
[SAY] The pipeline has four stages: Ingest, Validate, Transform, and Metrics.
[SHOW] Switch to terminal, open logs folder

[TIME] 2:29
[SAY] Ingest loads the CSV files and calls the Brasil API.
[SHOW] logs/pipeline_*.log - scroll to INGEST section

[TIME] 2:35
[SAY] Validate profiles each table and applies eight validation rules.
[SHOW] logs/pipeline_*.log - scroll to VALIDATE section

[TIME] 2:41
[SAY] Transform reconstructs the event sequence for each order and calculates outcomes.
[SHOW] logs/pipeline_*.log - scroll to TRANSFORM section

[TIME] 2:47
[SAY] Metrics computes the five delivery reliability KPIs.
[SHOW] logs/pipeline_*.log - scroll to METRICS section

[TIME] 2:53
[SAY] Each stage logs rows in, rows processed, rows out — complete audit trail.
[SHOW] logs/pipeline_*.log - show logging pattern (timestamps, row counts)

[TIME] 3:00
[SAY] The pipeline is idempotent: running it again on the same input produces the same output.
[SHOW] logs/pipeline_*.log - bottom showing METRICS COMPLETE

[TIME] 3:06
[SAY] The full run takes about ninety seconds end to end.
[SHOW] Terminal showing completed pipeline log

[TIME] 3:13
[SAY] The evidence table shows five metrics tied to stakeholder questions.
[SHOW] Open data/modeled/output/metrics_evidence_table.csv

[TIME] 3:19
[SAY] First: ninety-one point eight eight percent on-time delivery. Leadership's headline number.
[SHOW] metrics_evidence_table.csv - On-Time Delivery Rate row

[TIME] 3:26
[SAY] This comes from eighty-eight thousand six hundred twelve on-time orders out of ninety-six thousand four hundred thirty-eight valid orders.
[SHOW] metrics_evidence_table.csv - numerator and denominator columns highlighted

[TIME] 3:34
[SAY] Second: late orders are late by an average of eight point eight seven days.
[SHOW] metrics_evidence_table.csv - Average Delay row

[TIME] 3:40
[SAY] That's seven thousand eight hundred twenty-six late orders showing systemic delay issues.
[SHOW] metrics_evidence_table.csv - numerator showing "7,826 late orders"

[TIME] 3:47
[SAY] Third: twenty-seven states analyzed, worst is Alagoas at seventy-six point one percent on-time.
[SHOW] Open data/modeled/output/metrics_summary.md - State-by-State Performance table

[TIME] 3:54
[SAY] Only three hundred ninety-seven orders from Alagoas, but seventy-six percent on-time is a problem.
[SHOW] metrics_summary.md - AL row highlighted

[TIME] 4:01
[SAY] Operations should investigate carrier relationships in Alagoas specifically.
[SHOW] metrics_summary.md - state table

[TIME] 4:08
[SAY] Fourth: on-time orders score four point two nine stars, late orders score two point five seven.
[SHOW] metrics_evidence_table.csv - Review Score Correlation row

[TIME] 4:15
[SAY] That's a gap of one point seven three stars showing late delivery hurts satisfaction.
[SHOW] metrics_evidence_table.csv - Delta: -1.73

[TIME] 4:22
[SAY] Customer Experience can use this to prioritize delivery improvements.
[SHOW] metrics_evidence_table.csv - stakeholder: Customer Experience

[TIME] 4:29
[SAY] Fifth: delay split. Twenty-one percent of total time is before carrier handoff, seventy-nine percent in transit.
[SHOW] metrics_evidence_table.csv - Delay Split row

[TIME] 4:37
[SAY] Most of the delay is the carrier's responsibility, not internal ops — so focus improvement efforts there.
[SHOW] metrics_evidence_table.csv - notes column for Delay Split

[TIME] 4:45
[SAY] Leadership can trust ninety-one point eight eight percent because I refused to guess on three percent of orders. An honest number is more valuable than a precise wrong one.
[SHOW] Close all files, return to terminal or blank slide