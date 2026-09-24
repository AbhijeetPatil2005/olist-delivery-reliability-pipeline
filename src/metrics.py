"""
Metrics Module — FDE Data Foundations Pipeline

Computes 5 delivery reliability metrics:
1. On-Time Delivery Rate
2. Average Delay (Late Orders Only)
3. Delivery Reliability by State
4. Review Score Correlation with Lateness
5. Delay Split (Pre-Ship vs. In-Transit)

Outputs evidence table for stakeholder review.
"""

import pandas as pd
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

# Configuration - use Path for cross-platform consistency
MODELED_INTERMEDIATE_DIR = Path("data/modeled/intermediate")
MODELED_OUTPUT_DIR = Path("data/modeled/output")

# Evidence table output path
EVIDENCE_TABLE_PATH = MODELED_OUTPUT_DIR / "metrics_evidence_table.csv"
SUMMARY_MD_PATH = MODELED_OUTPUT_DIR / "metrics_summary.md"


def setup_logging() -> logging.Logger:
    """Configure logging for metrics stage."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = Path("logs") / f"metrics_{timestamp}.log"
    
    logger = logging.getLogger("metrics")
    logger.setLevel(logging.INFO)
    
    file_handler = logging.FileHandler(log_filename, mode='w')
    console_handler = logging.StreamHandler(sys.stdout)
    
    formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger, log_filename


def load_intermediate_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load intermediate data from transform stage."""
    orders_path = MODELED_INTERMEDIATE_DIR / "orders_enriched.csv"
    events_path = MODELED_INTERMEDIATE_DIR / "order_events.csv"
    state_path = MODELED_INTERMEDIATE_DIR / "state_aggregations.csv"
    
    if not orders_path.exists():
        raise FileNotFoundError(f"Orders not found: {orders_path}")
    
    orders_df = pd.read_csv(orders_path)
    events_df = pd.read_csv(events_path) if events_path.exists() else pd.DataFrame()
    state_df = pd.read_csv(state_path) if state_path.exists() else pd.DataFrame()
    
    return orders_df, events_df, state_df


def compute_on_time_rate(orders_df: pd.DataFrame, logger: logging.Logger) -> Dict:
    """Metric 1: On-Time Delivery Rate"""
    logger.info("=" * 60)
    logger.info("METRIC 1: ON-TIME DELIVERY RATE")
    logger.info("=" * 60)
    
    total_valid = len(orders_df)
    on_time_count = orders_df['on_time'].sum()
    on_time_rate = (on_time_count / total_valid * 100) if total_valid > 0 else 0
    
    logger.info(f"  Numerator: {on_time_count:,} on-time orders")
    logger.info(f"  Denominator: {total_valid:,} orders with valid delivery")
    logger.info(f"  Result: {on_time_rate:.2f}%")
    
    return {
        "metric_name": "On-Time Delivery Rate",
        "metric_value": f"{on_time_rate:.2f}%",
        "numerator": f"{on_time_count:,}",
        "denominator": f"{total_valid:,}",
        "time_period": "All-time (dataset)",
        "stakeholder": "Leadership",
        "notes": "Excludes orders with delivery_status_unclear (missing/invalid timestamps)",
        "stakeholder_notes": "Headline KPI for monthly reporting and carrier SLA negotiation"
    }


def compute_avg_delay(orders_df: pd.DataFrame, logger: logging.Logger) -> Dict:
    """Metric 2: Average Delay (Late Orders Only)"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("METRIC 2: AVERAGE DELAY (LATE ORDERS)")
    logger.info("=" * 60)
    
    late_orders = orders_df[~orders_df['on_time']]
    late_count = len(late_orders)
    
    if late_count > 0:
        avg_delay = late_orders['delay_days'].mean()
        logger.info(f"  Late orders analyzed: {late_count:,}")
        logger.info(f"  Mean delay: {avg_delay:.2f} days")
        logger.info(f"  Median delay: {late_orders['delay_days'].median():.2f} days")
    else:
        avg_delay = 0
        logger.info("  No late orders found")
    
    return {
        "metric_name": "Average Delay (Late Orders Only)",
        "metric_value": f"{avg_delay:.2f} days",
        "numerator": f"{late_count:,} late orders",
        "denominator": "N/A (late orders only)",
        "time_period": "All-time (dataset)",
        "stakeholder": "Operations",
        "notes": "Calculated as (actual_delivery - estimated_delivery) for orders where actual > estimated",
        "stakeholder_notes": "Shows magnitude of delay for the minority of orders that miss their deadline"
    }


def compute_delivery_by_state(state_df: pd.DataFrame, logger: logging.Logger) -> Dict:
    """Metric 3: Delivery Reliability by State"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("METRIC 3: DELIVERY RELIABILITY BY STATE")
    logger.info("=" * 60)
    
    if len(state_df) == 0:
        logger.warning("  No state data available")
        return {
            "metric_name": "Delivery Reliability by State",
            "metric_value": "N/A",
            "numerator": "N/A",
            "denominator": "N/A",
            "time_period": "N/A",
            "stakeholder": "Operations",
            "notes": "No state aggregations available",
            "stakeholder_notes": "Geographic analysis unavailable"
        }
    
    worst_states = state_df.nsmallest(3, 'on_time_rate')[['customer_state', 'on_time_rate', 'total_orders']]
    
    logger.info(f"  States analyzed: {len(state_df)}")
    logger.info(f"  Best state: {state_df.iloc[-1]['customer_state']} ({state_df.iloc[-1]['on_time_rate']:.1f}%)")
    logger.info(f"  Worst state: {state_df.iloc[0]['customer_state']} ({state_df.iloc[0]['on_time_rate']:.1f}%)")
    
    low_rate_count = int(state_df[state_df['on_time_rate'] < 50].shape[0])
    
    return {
        "metric_name": "Delivery Reliability by State",
        "metric_value": f"{len(state_df)} states analyzed",
        "numerator": f"{low_rate_count} states < 50%",
        "denominator": f"{len(state_df)} total states",
        "time_period": "All-time (dataset)",
        "stakeholder": "Operations",
        "notes": f"Worst state: {state_df.iloc[0]['customer_state']} ({state_df.iloc[0]['on_time_rate']:.1f}%)",
        "stakeholder_notes": "Identifies geographic areas needing carrier or logistics improvements"
    }


def compute_review_correlation(orders_df: pd.DataFrame, logger: logging.Logger) -> Dict:
    """Metric 4: Review Score vs. Delivery Lateness"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("METRIC 4: REVIEW SCORE vs. LATENESS")
    logger.info("=" * 60)
    
    orders_with_reviews = orders_df[orders_df['avg_review_score'] >= 0]
    
    on_time_reviews = orders_with_reviews[orders_with_reviews['on_time']]['avg_review_score'].mean()
    late_reviews = orders_with_reviews[~orders_with_reviews['on_time']]['avg_review_score'].mean()
    
    on_time_count = (orders_with_reviews['on_time']).sum()
    late_count = len(orders_with_reviews) - on_time_count
    
    score_delta = None
    if pd.notna(on_time_reviews) and pd.notna(late_reviews):
        score_delta = late_reviews - on_time_reviews
        logger.info(f"  On-time orders avg score: {on_time_reviews:.2f} ({on_time_count:,} orders)")
        logger.info(f"  Late orders avg score: {late_reviews:.2f} ({late_count:,} orders)")
        logger.info(f"  Impact: {score_delta:.2f} points {'lower' if score_delta < 0 else 'higher'} for late orders")
    else:
        logger.info("  Insufficient review data for analysis")
    
    return {
        "metric_name": "Review Score Correlation with Lateness",
        "metric_value": f"On-time: {on_time_reviews:.2f}, Late: {late_reviews:.2f}, Delta: {score_delta:.2f}" if score_delta else "Insufficient data",
        "numerator": f"{on_time_count + late_count} orders with reviews",
        "denominator": "N/A (comparison, not rate)",
        "time_period": "All-time (dataset)",
        "stakeholder": "Customer Experience",
        "notes": f"Delta of {score_delta:.2f} shows impact of late delivery on satisfaction" if score_delta else "No significant data available",
        "stakeholder_notes": "Quantifies customer experience impact of delivery reliability"
    }


def compute_delay_split(orders_df: pd.DataFrame, logger: logging.Logger) -> Dict:
    """Metric 5: Delay Split (Pre-Ship vs. In-Transit)"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("METRIC 5: DELAY SPLIT (PRE-SHIP vs. IN-TRANSIT)")
    logger.info("=" * 60)
    
    pre_ship_with_data = orders_df['pre_ship_days'].dropna()
    in_transit_with_data = orders_df['in_transit_days'].dropna()
    
    avg_pre_ship = pre_ship_with_data.mean() if len(pre_ship_with_data) > 0 else 0
    avg_in_transit = in_transit_with_data.mean() if len(in_transit_with_data) > 0 else 0
    total_avg = avg_pre_ship + avg_in_transit
    
    pre_ship_pct = (avg_pre_ship / total_avg * 100) if total_avg > 0 else 0
    in_transit_pct = (avg_in_transit / total_avg * 100) if total_avg > 0 else 0
    
    logger.info(f"  Avg order-to-ship (ops): {avg_pre_ship:.2f} days ({pre_ship_pct:.1f}%)")
    logger.info(f"  Avg in-transit (carrier): {avg_in_transit:.2f} days ({in_transit_pct:.1f}%)")
    
    return {
        "metric_name": "Delay Split (Pre-Ship vs. In-Transit)",
        "metric_value": f"Pre-ship: {avg_pre_ship:.2f}d ({pre_ship_pct:.1f}%), In-transit: {avg_in_transit:.2f}d ({in_transit_pct:.1f}%)",
        "numerator": f"Pre-ship: {len(pre_ship_with_data):,} orders, In-transit: {len(in_transit_with_data):,} orders",
        "denominator": "N/A (time breakdown, not count)",
        "time_period": "All-time (dataset)",
        "stakeholder": "Operations",
        "notes": "Pre-ship: order_approved_at -> order_delivered_carrier_date (ops responsibility)",
        "stakeholder_notes": "Identifies whether to focus improvements on internal processes or carrier relationships"
    }


def generate_evidence_table(metrics: list, orders_df: pd.DataFrame, state_df: pd.DataFrame, logger: logging.Logger) -> None:
    """Generate evidence table CSV and markdown summary."""
    MODELED_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    evidence_df = pd.DataFrame(metrics)
    csv_cols = ['metric_name', 'metric_value', 'numerator', 'denominator', 'time_period', 'stakeholder', 'notes']
    evidence_df[csv_cols].to_csv(EVIDENCE_TABLE_PATH, index=False)
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("GENERATING EVIDENCE TABLE")
    logger.info("=" * 60)
    logger.info(f"  [OK] Evidence table saved to: {EVIDENCE_TABLE_PATH}")
    
    generate_markdown_summary(metrics, orders_df, state_df, logger)


def generate_markdown_summary(metrics: list, orders_df: pd.DataFrame, state_df: pd.DataFrame, logger: logging.Logger) -> None:
    """Generate human-readable markdown summary."""
    lines = [
        "# Olist Delivery Reliability — Metrics Summary\n",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        "---\n",
        "## Executive Summary\n",
        f"- **Total Valid Orders Analyzed:** {len(orders_df):,}\n",
        f"- **On-Time Delivery Rate:** {metrics[0]['metric_value']}\n",
        f"- **Average Delay (Late Orders):** {metrics[1]['metric_value']}\n",
        f"- **States with <50% On-Time:** {metrics[2]['numerator']}\n",
        "---\n",
        "## Detailed Metrics\n"
    ]
    
    for m in metrics:
        lines.append(f"### {m['metric_name']}\n")
        lines.append(f"- **Value:** `{m['metric_value']}`\n")
        lines.append(f"- **Stakeholder:** {m['stakeholder']}\n")
        lines.append(f"- **Notes:** {m['notes']}\n")
        lines.append(f"- **For Decision:** {m['stakeholder_notes']}\n")
        lines.append("\n")
    
    if len(state_df) > 0:
        lines.append("---\n")
        lines.append("## State-by-State Performance\n")
        lines.append("| State | Orders | On-Time Rate | Avg Delay | Pre-Ship | In-Transit |\n")
        lines.append("|-------|--------|--------------|-----------|----------|------------|\n")
        for _, row in state_df.head(10).iterrows():
            lines.append(f"| {row['customer_state']} | {int(row['total_orders']):,} | {row['on_time_rate']:.1f}% | {row['avg_delay_days']:.1f}d | {row['avg_pre_ship_days']:.1f}d | {row['avg_in_transit_days']:.1f}d |\n")
        lines.append("\n*Top 10 worst-performing states. Full data in `data/modeled/intermediate/state_aggregations.csv`*\n")
    
    lines.append("---\n")
    lines.append("## Methodology Notes\n")
    lines.append("1. Orders with missing or impossible delivery timestamps are excluded from KPI calculations\n")
    lines.append("2. Holidays are logged as context but do not reclassify on-time status\n")
    lines.append("3. All calculations use pandas with explicit, reproducible transformations\n")
    
    with open(SUMMARY_MD_PATH, 'w') as f:
        f.writelines(lines)
    
    logger.info(f"  [OK] Markdown summary saved to: {SUMMARY_MD_PATH}")


def run_metrics() -> bool:
    """Main entry point for metrics stage."""
    start_time = datetime.now()
    logger, log_filename = setup_logging()
    
    logger.info("Starting METRICS stage...")
    
    try:
        orders_df, events_df, state_df = load_intermediate_data()
        logger.info(f"  [OK] Loaded {len(orders_df):,} orders, {len(state_df)} state aggregations")
    except FileNotFoundError as e:
        logger.error(f"  [X] {e}")
        logger.error("  Run src/transform_model.py first")
        return False
    
    metrics = []
    metrics.append(compute_on_time_rate(orders_df, logger))
    metrics.append(compute_avg_delay(orders_df, logger))
    metrics.append(compute_delivery_by_state(state_df, logger))
    metrics.append(compute_review_correlation(orders_df, logger))
    metrics.append(compute_delay_split(orders_df, logger))
    
    generate_evidence_table(metrics, orders_df, state_df, logger)
    
    duration = (datetime.now() - start_time).total_seconds()
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"METRICS COMPLETE ({duration:.2f}s)")
    logger.info("=" * 60)
    
    return True


if __name__ == "__main__":
    success = run_metrics()
    exit(0 if success else 1)