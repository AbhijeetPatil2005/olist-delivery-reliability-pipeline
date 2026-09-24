"""
Transform/Model Module â€” FDE Data Foundations Pipeline

Handles:
1. Event sequence reconstruction per order
2. Delivery outcome calculations
3. State-level aggregations
4. Holiday proximity enrichment
"""

import pandas as pd
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple, List
from dateutil.relativedelta import relativedelta

# Configuration - use Path for cross-platform consistency
RAW_FERIADOS_DIR = Path("data/raw/feriados")
VALIDATED_DIR = Path("data/validated")
MODELED_DIR = Path("data/modeled")
MODELED_INTERMEDIATE_DIR = MODELED_DIR / "intermediate"
MODELED_OUTPUT_DIR = MODELED_DIR / "output"
MODELED_DIR = Path("data/modeled")
MODELED_INTERMEDIATE_DIR = MODELED_DIR / "intermediate"
MODELED_OUTPUT_DIR = MODELED_DIR / "output"


def setup_logging() -> logging.Logger:
    """Configure logging for transform stage."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = Path("logs") / f"transform_{timestamp}.log"
    
    logger = logging.getLogger("transform")
    logger.setLevel(logging.INFO)
    
    file_handler = logging.FileHandler(log_filename, mode='w')
    console_handler = logging.StreamHandler(sys.stdout)
    
    formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger, log_filename


def load_holidays() -> Dict[str, list]:
    """Load cached Brazilian holidays from raw data."""
    holidays = {}
    if RAW_FERIADOS_DIR.exists():
        for f in RAW_FERIADOS_DIR.glob("brasil_holidays_*.json"):
            year = int(f.stem.split("_")[-1])
            with open(f, 'r', encoding='utf-8') as file:
                holidays[year] = json.load(file)
    return holidays


def calculate_days_from_nearest_holiday(order_date, holidays: Dict[str, list]) -> int:
    """
    Calculate days from nearest Brazilian national holiday.
    
    Returns:
        Minimum days to any holiday within +/- 7 days, or None if no holidays nearby
    """
    if pd.isna(order_date):
        return None
    
    try:
        order_dt = pd.to_datetime(order_date)
        year = order_dt.year
        
        if str(year) not in holidays or not holidays[str(year)]:
            return None
        
        min_days = None
        for holiday in holidays[str(year)]:
            holiday_date = pd.to_datetime(holiday['date'])
            days_diff = abs((order_dt - holiday_date).days)
            
            if days_diff <= 7:  # Only consider holidays within 7 days
                if min_days is None or days_diff < min_days:
                    min_days = days_diff
        
        return min_days
    except Exception:
        return None


def reconstruct_event_sequence(orders_df: pd.DataFrame, holidays: Dict[str, list], logger: logging.Logger) -> pd.DataFrame:
    """
    Reconstruct the event sequence for each order.
    
    Events: placed, approved, shipped, delivered, reviewed
    """
    logger.info("=" * 60)
    logger.info("RECONSTRUCTING EVENT SEQUENCES")
    logger.info("=" * 60)
    
    # Parse timestamps
    date_cols = [
        'order_purchase_timestamp', 'order_approved_at',
        'order_delivered_carrier_date', 'order_delivered_customer_date',
        'order_estimated_delivery_date'
    ]
    
    for col in date_cols:
        orders_df[col] = pd.to_datetime(orders_df[col], errors='coerce')
    
    # Create event dataframe
    events = []
    
    for idx, row in orders_df.iterrows():
        order_id = row['order_id']
        customer_id = row.get('customer_id')
        state = row.get('customer_state')
        
        # Event 1: Order placed
        if pd.notna(row['order_purchase_timestamp']):
            events.append({
                'order_id': order_id,
                'customer_id': customer_id,
                'customer_state': state,
                'event_type': 'placed',
                'event_timestamp': row['order_purchase_timestamp']
            })
        
        # Event 2: Order approved
        if pd.notna(row['order_approved_at']):
            events.append({
                'order_id': order_id,
                'customer_id': customer_id,
                'customer_state': state,
                'event_type': 'approved',
                'event_timestamp': row['order_approved_at']
            })
        
        # Event 3: Order shipped (carrier handoff)
        if pd.notna(row['order_delivered_carrier_date']):
            events.append({
                'order_id': order_id,
                'customer_id': customer_id,
                'customer_state': state,
                'event_type': 'shipped',
                'event_timestamp': row['order_delivered_carrier_date']
            })
        
        # Event 4: Order delivered
        if pd.notna(row['order_delivered_customer_date']):
            events.append({
                'order_id': order_id,
                'customer_id': customer_id,
                'customer_state': state,
                'event_type': 'delivered',
                'event_timestamp': row['order_delivered_customer_date']
            })
    
    events_df = pd.DataFrame(events)
    
    if len(events_df) > 0:
        events_df = events_df.sort_values(['order_id', 'event_timestamp'])
        MODELED_INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)
        events_df.to_csv(MODELED_INTERMEDIATE_DIR / "order_events.csv", index=False)
        logger.info(f"  âœ“ Saved {len(events_df):,} events for {events_df['order_id'].nunique():,} orders")
    else:
        logger.warning("  âš  No events reconstructed (possible data issue)")
    
    return events_df


def enrich_orders_with_outcomes(
    orders_df: pd.DataFrame,
    order_reviews_df: pd.DataFrame,
    holidays: Dict[str, list],
    logger: logging.Logger
) -> pd.DataFrame:
    """
    Enrich orders with delivery outcomes and delay calculations.
    
    Computes:
    - on_time: delivered <= estimated
    - delay_days: delivered - estimated (if late)
    - days_from_nearest_holiday: context for analysis
    """
    logger.info("")
    logger.info("=" * 60)
    logger.info("CALCULATING DELIVERY OUTCOMES")
    logger.info("=" * 60)
    
    # Calculate on-time and delay
    orders_df['on_time'] = pd.to_datetime(orders_df['order_delivered_customer_date']) <= \
                           pd.to_datetime(orders_df['order_estimated_delivery_date'])
    
    orders_df['delay_days'] = (
        pd.to_datetime(orders_df['order_delivered_customer_date']) - 
        pd.to_datetime(orders_df['order_estimated_delivery_date'])
    ).dt.days
    
    # Only positive delays are "late"
    orders_df['delay_days'] = orders_df['delay_days'].apply(lambda x: x if x > 0 else 0)
    
    # Calculate pre-ship lag (order approved â†’ shipped)
    orders_df['pre_ship_days'] = (
        pd.to_datetime(orders_df['order_delivered_carrier_date']) - 
        pd.to_datetime(orders_df['order_approved_at'])
    ).dt.days
    orders_df['pre_ship_days'] = orders_df['pre_ship_days'].apply(lambda x: x if pd.notna(x) and x >= 0 else None)
    
    # Calculate in-transit lag (shipped â†’ delivered)
    orders_df['in_transit_days'] = (
        pd.to_datetime(orders_df['order_delivered_customer_date']) - 
        pd.to_datetime(orders_df['order_delivered_carrier_date'])
    ).dt.days
    orders_df['in_transit_days'] = orders_df['in_transit_days'].apply(lambda x: x if pd.notna(x) and x >= 0 else None)
    
    # Calculate holiday proximity
    logger.info("  Calculating holiday proximity...")
    orders_df['days_from_nearest_holiday'] = orders_df['order_purchase_timestamp'].apply(
        lambda x: calculate_days_from_nearest_holiday(x, holidays)
    )
    holiday_context_count = orders_df['days_from_nearest_holiday'].notna().sum()
    logger.info(f"    â†’ {holiday_context_count:,} orders with holiday context")
    
    # Add review score (join from reviews)
    if 'order_id' in order_reviews_df.columns and 'review_score' in order_reviews_df.columns:
        reviews_by_order = order_reviews_df.groupby('order_id')['review_score'].mean().reset_index()
        reviews_by_order.columns = ['order_id', 'avg_review_score']
        orders_df = orders_df.merge(reviews_by_order, on='order_id', how='left')
        orders_df['avg_review_score'] = orders_df['avg_review_score'].fillna(-1)  # -1 = no review
    
    # Select final columns for output
    output_cols = [
        'order_id', 'customer_id', 'customer_state',
        'order_purchase_timestamp', 'order_approved_at',
        'order_delivered_carrier_date', 'order_delivered_customer_date',
        'order_estimated_delivery_date',
        'on_time', 'delay_days', 'pre_ship_days', 'in_transit_days',
        'days_from_nearest_holiday', 'avg_review_score'
    ]
    
    # Filter to only columns that exist
    output_cols = [c for c in output_cols if c in orders_df.columns]
    enriched_orders = orders_df[output_cols].copy()
    
    # Save to file
    enriched_orders.to_csv(MODELED_INTERMEDIATE_DIR / "orders_enriched.csv", index=False)
    
    logger.info(f"  âœ“ Saved {len(enriched_orders):,} enriched orders")
    logger.info(f"    â†’ On-time rate: {(enriched_orders['on_time'].sum() / len(enriched_orders) * 100):.2f}%")
    logger.info(f"    â†’ Mean delay (late orders): {enriched_orders[~enriched_orders['on_time']]['delay_days'].mean():.2f} days")
    
    return enriched_orders


def build_state_aggregations(enriched_orders: pd.DataFrame, logger: logging.Logger) -> pd.DataFrame:
    """
    Build state-level delivery performance aggregations.
    """
    logger.info("")
    logger.info("=" * 60)
    logger.info("BUILDING STATE-LEVEL AGGREGATIONS")
    logger.info("=" * 60)
    
    # Group by customer state
    state_stats = enriched_orders.groupby('customer_state').agg({
        'order_id': 'count',
        'on_time': ['sum', 'mean'],
        'delay_days': 'mean',
        'pre_ship_days': 'mean',
        'in_transit_days': 'mean',
        'avg_review_score': 'mean'
    }).reset_index()
    
    # Flatten column names
    state_stats.columns = [
        'customer_state',
        'total_orders',
        'on_time_orders',
        'on_time_rate',
        'avg_delay_days',
        'avg_pre_ship_days',
        'avg_in_transit_days',
        'avg_review_score'
    ]
    
    # Convert on_time_rate to percentage
    state_stats['on_time_rate'] = (state_stats['on_time_rate'] * 100).round(2)
    state_stats['avg_delay_days'] = state_stats['avg_delay_days'].round(2)
    state_stats['avg_pre_ship_days'] = state_stats['avg_pre_ship_days'].round(2)
    state_stats['avg_in_transit_days'] = state_stats['avg_in_transit_days'].round(2)
    state_stats['avg_review_score'] = state_stats['avg_review_score'].round(2)
    
    # Sort by on_time_rate ascending (worst first)
    state_stats = state_stats.sort_values('on_time_rate', ascending=True)
    
    # Save to file
    state_stats.to_csv(MODELED_INTERMEDIATE_DIR / "state_aggregations.csv", index=False)
    
    logger.info(f"  âœ“ Saved aggregations for {len(state_stats)} states")
    logger.info(f"    â†’ Best state: {state_stats.iloc[-1]['customer_state']} ({state_stats.iloc[-1]['on_time_rate']:.1f}%)")
    logger.info(f"    â†’ Worst state: {state_stats.iloc[0]['customer_state']} ({state_stats.iloc[0]['on_time_rate']:.1f}%)")
    
    return state_stats


def run_transform() -> bool:
    """
    Main entry point for transform/model stage.
    
    Returns:
        True if transform succeeded, False otherwise
    """
    start_time = datetime.now()
    logger, log_filename = setup_logging()
    
    logger.info("Starting TRANSFORM/MODEL stage...")
    
    # Load validated orders
    orders_path = VALIDATED_DIR / "orders_validated.csv"
    if not orders_path.exists():
        logger.error(f"  âœ— Validated orders not found: {orders_path}")
        logger.error("  Run src/validate.py first to generate validated data")
        return False
    
    orders_df = pd.read_csv(orders_path)
    logger.info(f"  âœ“ Loaded {len(orders_df):,} validated orders")
    
    # Load order reviews for enrichment
    reviews_path = VALIDATED_DIR.parent / "raw" / "olist" / "olist_order_reviews_dataset.csv"
    if reviews_path.exists():
        order_reviews_df = pd.read_csv(reviews_path)
        logger.info(f"  âœ“ Loaded {len(order_reviews_df):,} reviews for enrichment")
    else:
        order_reviews_df = pd.DataFrame()
        logger.warning("  âš  Order reviews not found, skipping review enrichment")
    
    # Load holidays
    holidays = load_holidays()
    logger.info(f"  âœ“ Loaded holidays for {len(holidays)} years")
    
    # Step 1: Reconstruct event sequences
    events_df = reconstruct_event_sequence(orders_df.copy(), holidays, logger)
    
    # Step 2: Enrich orders with outcomes
    enriched_orders = enrich_orders_with_outcomes(orders_df, order_reviews_df, holidays, logger)
    
    # Step 3: Build state aggregations
    state_stats = build_state_aggregations(enriched_orders, logger)
    
    duration = (datetime.now() - start_time).total_seconds()
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"TRANSFORM COMPLETE ({duration:.2f}s)")
    logger.info("=" * 60)
    logger.info(f"Intermediate files in: {MODELED_INTERMEDIATE_DIR}")
    
    return True


if __name__ == "__main__":
    success = run_transform()
    exit(0 if success else 1)
