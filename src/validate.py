"""
Validation Module â€” FDE Data Foundations Pipeline

Handles:
1. Table profiling (nulls, duplicates, value ranges)
2. Business-oriented validation rules
3. Flagging and reporting of data quality issues
"""

import pandas as pd
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple, List, Any
import sys

# Configuration - use Path for cross-platform consistency
RAW_OLIST_DIR = Path("data/raw/olist")
RAW_FERIADOS_DIR = Path("data/raw/feriados")
VALIDATED_DIR = Path("data/validated")
VALIDATION_LOG_DIR = Path("logs")

# Expected columns for each table (required fields)
REQUIRED_COLUMNS = {
    "orders": [
        "order_id", "customer_id", "order_status",
        "order_purchase_timestamp", "order_approved_at",
        "order_delivered_carrier_date", "order_delivered_customer_date",
        "order_estimated_delivery_date"
    ],
    "order_items": ["order_id", "order_item_id", "product_id", "seller_id", "price", "freight_value"],
    "order_payments": ["order_id", "payment_sequential", "payment_type", "payment_value"],
    "order_reviews": ["review_id", "order_id", "review_score", "review_creation_date"],
    "products": ["product_id", "product_category_name"],
    "sellers": ["seller_id"],
    "customers": ["customer_id"],
    "geolocation": ["geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng"],
    "category_translation": ["product_category_name", "product_category_name_english"],
}

# Validation rule definitions
VALIDATION_RULES = {
    "VAL-001": {
        "name": "delivery_timeline_impossible",
        "description": "delivered_customer_date < delivered_carrier_date (impossible timeline)",
        "table": "orders",
        "condition": lambda df: pd.to_datetime(df['order_delivered_customer_date'], errors='coerce') <
                                pd.to_datetime(df['order_delivered_carrier_date'], errors='coerce')
    },
    "VAL-002": {
        "name": "delivery_before_purchase",
        "description": "delivered_customer_date < order_purchase_timestamp (impossible)",
        "table": "orders",
        "condition": lambda df: pd.to_datetime(df['order_delivered_customer_date'], errors='coerce') <
                                pd.to_datetime(df['order_purchase_timestamp'], errors='coerce')
    },
    "VAL-003": {
        "name": "approval_before_purchase",
        "description": "order_approved_at < order_purchase_timestamp (impossible)",
        "table": "orders",
        "condition": lambda df: pd.to_datetime(df['order_approved_at'], errors='coerce') <
                                pd.to_datetime(df['order_purchase_timestamp'], errors='coerce')
    },
    "VAL-004": {
        "name": "invalid_review_score",
        "description": "review_score not in {1,2,3,4,5}",
        "table": "order_reviews",
        "condition": lambda df: ~df['review_score'].isin([1, 2, 3, 4, 5])
    },
    "VAL-005": {
        "name": "invalid_payment_value",
        "description": "payment_value <= 0",
        "table": "order_payments",
        "condition": lambda df: df['payment_value'] <= 0
    },
    "VAL-006": {
        "name": "orphan_order_item",
        "description": "order_id in order_items not found in orders",
        "table": "order_items",
        "condition": None  # Special FK check
    },
    "VAL-007": {
        "name": "orphan_review",
        "description": "order_id in order_reviews not found in orders",
        "table": "order_reviews",
        "condition": None  # Special FK check
    },
    "VAL-008": {
        "name": "orphan_payment",
        "description": "order_id in order_payments not found in orders",
        "table": "order_payments",
        "condition": None  # Special FK check
    },
}


def setup_logging() -> logging.Logger:
    """Configure logging for validation stage."""
    VALIDATION_LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = VALIDATION_LOG_DIR / f"validate_{timestamp}.log"
    
    logger = logging.getLogger("validate")
    logger.setLevel(logging.INFO)
    
    file_handler = logging.FileHandler(log_filename, mode='w')
    console_handler = logging.StreamHandler(sys.stdout)
    
    formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger, log_filename


def load_olist_table(filename: str) -> Tuple[pd.DataFrame, bool]:
    """
    Load an Olist CSV file.
    
    Returns:
        Tuple of (DataFrame, load_success)
    """
    filepath = RAW_OLIST_DIR / filename
    if not filepath.exists():
        return None, False
    
    try:
        df = pd.read_csv(filepath, encoding='utf-8')
        return df, True
    except Exception as e:
        return None, False


def profile_table(df: pd.DataFrame, table_name: str, logger: logging.Logger) -> Dict[str, Any]:
    """
    Profile a DataFrame: nulls, duplicates, value ranges.
    
    Returns:
        Dictionary with profiling stats
    """
    stats = {
        "table_name": table_name,
        "total_rows": len(df),
        "columns": {}
    }
    
    logger.info(f"  Profiling {table_name} ({len(df):,} rows, {len(df.columns)} columns)...")
    
    for col in df.columns:
        col_stats = {
            "dtype": str(df[col].dtype),
            "null_count": int(df[col].isna().sum()),
            "null_pct": round(df[col].isna().sum() / len(df) * 100, 2),
            "unique_count": int(df[col].nunique()),
        }
        
        # Duplicate count for this column (if meaningful key)
        if df[col].nunique() < len(df) * 0.9:
            col_stats["duplicate_count"] = int(df[col].duplicated().sum())
        
        # Value range for numeric
        if pd.api.types.is_numeric_dtype(df[col]):
            col_stats["min"] = float(df[col].min()) if not df[col].empty else None
            col_stats["max"] = float(df[col].max()) if not df[col].empty else None
            col_stats["mean"] = round(float(df[col].mean()), 2) if not df[col].empty else None
        
        # Value range for dates
        if 'timestamp' in col.lower() or 'date' in col.lower():
            try:
                dates = pd.to_datetime(df[col], errors='coerce').dropna()
                if len(dates) > 0:
                    col_stats["min_date"] = str(dates.min())
                    col_stats["max_date"] = str(dates.max())
            except:
                pass
        
        stats["columns"][col] = col_stats
    
    logger.info(f"    â†’ {stats['total_rows']:,} rows, {stats['columns']['null_count'] if 'null_count' in stats else 0:,} nulls")
    
    return stats


def check_foreign_keys(
    orders_df: pd.DataFrame,
    child_table_name: str,
    child_df: pd.DataFrame,
    child_fk_column: str,
    logger: logging.Logger
) -> List[str]:
    """
    Check foreign key integrity: find order_ids in child table not in orders.
    
    Returns:
        List of order_ids that are orphaned
    """
    valid_order_ids = set(orders_df['order_id'].dropna())
    child_order_ids = set(child_df[child_fk_column].dropna())
    
    orphaned = child_order_ids - valid_order_ids
    
    if len(orphaned) > 0:
        logger.warning(f"    âš  {child_table_name}: {len(orphaned):,} orphaned {child_fk_column}s ({child_fk_column}s in child not in orders)")
    
    return list(orphaned)


def apply_validation_rules(
    orders_df: pd.DataFrame,
    order_items_df: pd.DataFrame,
    order_payments_df: pd.DataFrame,
    order_reviews_df: pd.DataFrame,
    logger: logging.Logger
) -> Dict[str, Dict]:
    """
    Apply all validation rules and collect flagged records.
    
    Returns:
        Dictionary of rule_id -> {count, sample_indices}
    """
    logger.info("")
    logger.info("=" * 60)
    logger.info("APPLYING VALIDATION RULES")
    logger.info("=" * 60)
    
    flagged_results = {}
    
    # Rule VAL-001: Impossible delivery timeline
    logger.info("  Applying VAL-001: delivery_timeline_impossible...")
    mask = pd.to_datetime(orders_df['order_delivered_customer_date'], errors='coerce') < \
           pd.to_datetime(orders_df['order_delivered_carrier_date'], errors='coerce')
    count = mask.sum()
    flagged_results["VAL-001"] = {"count": int(count), "flag": "delivery_timeline_impossible"}
    logger.info(f"    â†’ {count:,} flagged")
    
    # Rule VAL-002: Delivery before purchase
    logger.info("  Applying VAL-002: delivery_before_purchase...")
    mask = pd.to_datetime(orders_df['order_delivered_customer_date'], errors='coerce') < \
           pd.to_datetime(orders_df['order_purchase_timestamp'], errors='coerce')
    count = mask.sum()
    flagged_results["VAL-002"] = {"count": int(count), "flag": "delivery_before_purchase"}
    logger.info(f"    â†’ {count:,} flagged")
    
    # Rule VAL-003: Approval before purchase
    logger.info("  Applying VAL-003: approval_before_purchase...")
    mask = pd.to_datetime(orders_df['order_approved_at'], errors='coerce') < \
           pd.to_datetime(orders_df['order_purchase_timestamp'], errors='coerce')
    count = mask.sum()
    flagged_results["VAL-003"] = {"count": int(count), "flag": "approval_before_purchase"}
    logger.info(f"    â†’ {count:,} flagged")
    
    # Rule VAL-004: Invalid review score
    logger.info("  Applying VAL-004: invalid_review_score...")
    mask = ~order_reviews_df['review_score'].isin([1, 2, 3, 4, 5])
    count = mask.sum()
    flagged_results["VAL-004"] = {"count": int(count), "flag": "invalid_review_score"}
    logger.info(f"    â†’ {count:,} flagged")
    
    # Rule VAL-005: Invalid payment value
    logger.info("  Applying VAL-005: invalid_payment_value...")
    mask = order_payments_df['payment_value'] <= 0
    count = mask.sum()
    flagged_results["VAL-005"] = {"count": int(count), "flag": "invalid_payment_value"}
    logger.info(f"    â†’ {count:,} flagged")
    
    # Rule VAL-006: Orphan order_items
    logger.info("  Applying VAL-006: orphan_order_item...")
    orphaned = check_foreign_keys(orders_df, "order_items", order_items_df, "order_id", logger)
    flagged_results["VAL-006"] = {"count": len(orphaned), "flag": "orphan_order_item"}
    
    # Rule VAL-007: Orphan reviews
    logger.info("  Applying VAL-007: orphan_review...")
    orphaned = check_foreign_keys(orders_df, "order_reviews", order_reviews_df, "order_id", logger)
    flagged_results["VAL-007"] = {"count": len(orphaned), "flag": "orphan_review"}
    
    # Rule VAL-008: Orphan payments
    logger.info("  Applying VAL-008: orphan_payment...")
    orphaned = check_foreign_keys(orders_df, "order_payments", order_payments_df, "order_id", logger)
    flagged_results["VAL-008"] = {"count": len(orphaned), "flag": "orphan_payment"}
    
    return flagged_results


def write_validated_orders(
    orders_df: pd.DataFrame,
    flagged_results: Dict[str, Dict],
    logger: logging.Logger
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Write validated orders with delivery_status_unclear flag.
    
    Returns:
        Tuple of (valid_orders, excluded_orders)
    """
    VALIDATED_DIR.mkdir(parents=True, exist_ok=True)
    
    # Identify delivery_status_unclear orders
    # These have: missing delivered_customer_date OR impossible timeline
    delivered_is_null = orders_df['order_delivered_customer_date'].isna()
    impossible_timeline = flagged_results["VAL-001"]["count"] > 0
    
    # Mark delivery_status_unclear
    delivery_impossible_mask = pd.to_datetime(
        orders_df['order_delivered_customer_date'], errors='coerce'
    ) < pd.to_datetime(
        orders_df['order_delivered_carrier_date'], errors='coerce'
    )
    
    delivery_status = []
    for idx, row in orders_df.iterrows():
        delivered = pd.notna(row['order_delivered_customer_date'])
        delivered_carrier = pd.notna(row['order_delivered_carrier_date'])
        approved = pd.notna(row['order_approved_at'])
        purchased = pd.notna(row['order_purchase_timestamp'])
        timeline_possible = not delivery_impossible_mask.get(idx, False)
        
        if not delivered:
            status = "delivery_missing"  # Never delivered (still in transit or canceled)
        elif not timeline_possible:
            status = "delivery_timeline_impossible"
        elif not purchased:
            status = "purchase_timestamp_missing"
        elif not approved:
            status = "approval_timestamp_missing"
        elif not delivered_carrier:
            status = "carrier_timestamp_missing"
        else:
            status = "valid_delivery"
        
        delivery_status.append(status)
    
    orders_df['delivery_status'] = delivery_status
    
    # Split into valid and excluded
    valid_orders = orders_df[orders_df['delivery_status'] == 'valid_delivery'].copy()
    excluded_orders = orders_df[orders_df['delivery_status'] != 'valid_delivery'].copy()
    
    # Add on_time flag for valid orders
    valid_orders['on_time'] = pd.to_datetime(valid_orders['order_delivered_customer_date']) <= \
                              pd.to_datetime(valid_orders['order_estimated_delivery_date'])
    
    # Save to files
    valid_orders.to_csv(VALIDATED_DIR / "orders_validated.csv", index=False)
    excluded_orders.to_csv(VALIDATED_DIR / "orders_excluded.csv", index=False)
    
    logger.info("")
    logger.info(f"  âœ“ Saved {len(valid_orders):,} valid orders to orders_validated.csv")
    logger.info(f"  âœ“ Saved {len(excluded_orders):,} excluded orders to orders_excluded.csv")
    logger.info(f"    â†’ Delivery status breakdown:")
    for status in orders_df['delivery_status'].value_counts().to_dict().items():
        logger.info(f"      - {status[0]}: {status[1]:,}")
    
    return valid_orders, excluded_orders


def generate_validation_report(
    profiling_stats: Dict,
    flagged_results: Dict,
    valid_orders_count: int,
    excluded_orders_count: int,
    logger: logging.Logger
) -> None:
    """Generate validation summary report."""
    VALIDATED_DIR.mkdir(parents=True, exist_ok=True)
    
    report = {
        "generated_at": datetime.now().isoformat(),
        "profiling": profiling_stats,
        "validation_rules": flagged_results,
        "delivery_outcomes": {
            "valid_orders": valid_orders_count,
            "excluded_orders": excluded_orders_count,
            "exclusion_rate": round(excluded_orders_count / (valid_orders_count + excluded_orders_count) * 100, 2) if (valid_orders_count + excluded_orders_count) > 0 else 0
        }
    }
    
    report_path = VALIDATED_DIR / "validation_summary.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    logger.info("")
    logger.info(f"  âœ“ Validation summary saved to {report_path}")
    logger.info(f"  â†’ Exclusion rate: {report['delivery_outcomes']['exclusion_rate']:.2f}%")


def run_validation() -> bool:
    """
    Main entry point for validation stage.
    
    Returns:
        True if validation succeeded, False otherwise
    """
    start_time = datetime.now()
    logger, log_filename = setup_logging()
    
    logger.info("Starting VALIDATION stage...")
    
    # Load all required tables
    logger.info("=" * 60)
    logger.info("LOADING TABLES FOR PROFILING")
    logger.info("=" * 60)
    
    tables = {}
    load_success = True
    
    table_files = [
        ("orders", "olist_orders_dataset.csv"),
        ("order_items", "olist_order_items_dataset.csv"),
        ("order_payments", "olist_order_payments_dataset.csv"),
        ("order_reviews", "olist_order_reviews_dataset.csv"),
        ("products", "olist_products_dataset.csv"),
        ("sellers", "olist_sellers_dataset.csv"),
        ("customers", "olist_customers_dataset.csv"),
        ("geolocation", "olist_geolocation_dataset.csv"),
        ("category_translation", "product_category_name_translation.csv"),
    ]
    
    for table_name, filename in table_files:
        df, success = load_olist_table(filename)
        if success:
            tables[table_name] = df
            logger.info(f"  âœ“ Loaded {table_name}: {len(df):,} rows")
        else:
            logger.error(f"  âœ— Failed to load {table_name} from {filename}")
            load_success = False
    
    if not load_success:
        logger.error("VALIDATION FAILED: Could not load all required tables")
        return False
    
    # Profile all tables
    logger.info("")
    logger.info("=" * 60)
    logger.info("PROFILING ALL TABLES")
    logger.info("=" * 60)
    
    profiling_stats = {}
    for table_name, df in tables.items():
        stats = profile_table(df, table_name, logger)
        profiling_stats[table_name] = stats
    
    # Apply validation rules
    flagged_results = apply_validation_rules(
        tables["orders"],
        tables["order_items"],
        tables["order_payments"],
        tables["order_reviews"],
        logger
    )
    
    # Join orders with customers to get customer_state for metrics
    orders_with_state = tables["orders"].merge(
        tables["customers"][["customer_id", "customer_state"]],
        on="customer_id",
        how="left"
    )
    
    # Write validated orders
    valid_orders, excluded_orders = write_validated_orders(
        orders_with_state,
        flagged_results,
        logger
    )
    
    # Generate report
    generate_validation_report(
        profiling_stats,
        flagged_results,
        len(valid_orders),
        len(excluded_orders),
        logger
    )
    
    duration = (datetime.now() - start_time).total_seconds()
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"VALIDATION COMPLETE ({duration:.2f}s)")
    logger.info("=" * 60)
    logger.info(f"Valid orders for metric calculation: {len(valid_orders):,}")
    logger.info(f"Excluded (delivery_status_unclear): {len(excluded_orders):,}")
    
    return True


if __name__ == "__main__":
    success = run_validation()
    exit(0 if success else 1)
