"""
Ingestion Module â€” FDE Data Foundations Pipeline

Handles retrieval of:
1. Olist CSV files (raw, immutable)
2. Brazilian Holidays API (via Brasil API)
3. Completeness verification with checksums
"""

import os
import hashlib
import json
import logging
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple, Optional

# Configuration
RAW_OLIST_DIR = Path("data/raw/olist")
RAW_FERIADOS_DIR = Path("data/raw/feriados")
LOG_DIR = Path("logs")

# Olist file manifest: filename -> expected row count (approximate)
OLIST_MANIFEST = {
    "olist_orders_dataset.csv": 99441,
    "olist_order_items_dataset.csv": 112650,
    "olist_order_payments_dataset.csv": 103886,
    "olist_order_reviews_dataset.csv": 100000,
    "olist_products_dataset.csv": 32951,
    "olist_sellers_dataset.csv": 3095,
    "olist_customers_dataset.csv": 99441,
    "olist_geolocation_dataset.csv": 1000163,
    "product_category_name_translation.csv": 71,
}

# Brasil API base URL
BRASIL_API_FERIADOS_URL = "https://brasilapi.com.br/api/feriados/v1"


def setup_logging() -> logging.Logger:
    """Configure logging to file and console."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = LOG_DIR / f"ingest_{timestamp}.log"
    
    logger = logging.getLogger("ingest")
    logger.setLevel(logging.INFO)
    
    # File handler
    file_handler = logging.FileHandler(log_filename, mode='w')
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger, log_filename


def compute_file_hash(filepath: Path) -> str:
    """Compute SHA256 hash of a file for integrity verification."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def verify_olist_completeness(logger: logging.Logger) -> Tuple[bool, Dict]:
    """
    Verify all Olist files are present and complete.
    
    Returns:
        Tuple of (all_present, manifest_results)
    """
    logger.info("=" * 60)
    logger.info("VERIFYING OLIST RAW FILES")
    logger.info("=" * 60)
    
    results = {}
    all_present = True
    
    for filename, expected_rows in OLIST_MANIFEST.items():
        filepath = RAW_OLIST_DIR / filename
        status = "OK"
        actual_rows = None
        file_hash = None
        
        if not filepath.exists():
            status = "MISSING"
            all_present = False
            logger.error(f"  [X] {filename}: MISSING")
        else:
            try:
                # Compute checksum
                file_hash = compute_file_hash(filepath)
                
                # Quick row count (first column)
                with open(filepath, 'r', encoding='utf-8') as f:
                    actual_rows = sum(1 for _ in f) - 1  # subtract header
                
                if actual_rows < expected_rows * 0.95:  # Allow 5% variance
                    status = "ROW_COUNT_LOW"
                    all_present = False
                    logger.warning(f"  âš  {filename}: {actual_rows} rows (expected ~{expected_rows})")
                else:
                    logger.info(f"  âœ“ {filename}: {actual_rows} rows, hash={file_hash[:8]}...")
                
            except Exception as e:
                status = f"ERROR: {str(e)}"
                all_present = False
                logger.error(f"  âœ— {filename}: {status}")
        
        results[filename] = {
            "expected_rows": expected_rows,
            "actual_rows": actual_rows,
            "status": status,
            "file_hash": file_hash[:16] if file_hash else None
        }
    
    # Summary
    logger.info("")
    logger.info(f"COMPLETENESS SUMMARY: {sum(1 for r in results.values() if r['status'] == 'OK')}/{len(results)} files OK")
    
    return all_present, results


def fetch_brasil_holidays(years: list, logger: logging.Logger) -> Dict[int, list]:
    """
    Fetch Brazilian national holidays for specified years via Brasil API.
    
    Args:
        years: List of years to fetch (e.g., [2023, 2024, 2025, 2026])
    
    Returns:
        Dictionary of year -> list of holidays
    """
    logger.info("=" * 60)
    logger.info("FETCHING BRAZILIAN HOLIDAYS VIA BRASIL API")
    logger.info("=" * 60)
    
    RAW_FERIADOS_DIR.mkdir(parents=True, exist_ok=True)
    all_holidays = {}
    
    for year in years:
        url = f"{BRASIL_API_FERIADOS_URL}/{year}"
        logger.info(f"Fetching holidays for {year}...")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                holidays = response.json()
                
                # Validate response structure
                if not isinstance(holidays, list):
                    logger.warning(f"  Unexpected response type for {year}: {type(holidays)}")
                    continue
                
                # Cache to file
                cache_file = RAW_FERIADOS_DIR / f"brasil_holidays_{year}.json"
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(holidays, f, ensure_ascii=False, indent=2)
                
                all_holidays[year] = holidays
                logger.info(f"  âœ“ {year}: {len(holidays)} holidays cached to {cache_file.name}")
                break
                
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    logger.warning(f"  Attempt {attempt + 1} failed: {e}, retrying...")
                else:
                    logger.error(f"  âœ— {year}: Failed after {max_retries} attempts - {e}")
    
    # Summary
    total_holidays = sum(len(h) for h in all_holidays.values())
    logger.info("")
    logger.info(f"HOLIDAYS SUMMARY: {len(all_holidays)} years, {total_holidays} total holidays")
    
    return all_holidays


def log_ingestion_summary(
    logger: logging.Logger,
    olist_results: Dict,
    holidays_results: Dict,
    duration_seconds: float
) -> None:
    """Log final ingestion summary."""
    logger.info("=" * 60)
    logger.info("INGESTION COMPLETE")
    logger.info("=" * 60)
    
    olist_ok = sum(1 for r in olist_results.values() if r['status'] == 'OK')
    olist_total = len(olist_results)
    
    logger.info(f"Duration: {duration_seconds:.2f} seconds")
    logger.info(f"Olist files: {olist_ok}/{olist_total} present and verified")
    logger.info(f"Brazil holidays: {len(holidays_results)} years fetched")
    logger.info(f"Raw data location: {RAW_OLIST_DIR}")
    logger.info(f"Holidays location: {RAW_FERIADOS_DIR}")
    logger.info("=" * 60)


def run_ingestion() -> Tuple[bool, Dict, Dict]:
    """
    Main entry point for ingestion stage.
    
    Returns:
        Tuple of (all_success, olist_results, holidays_results)
    """
    start_time = datetime.now()
    logger, log_filename = setup_logging()
    
    logger.info("Starting INGESTION stage...")
    
    # Verify Olist files
    olist_success, olist_results = verify_olist_completeness(logger)
    
    # Fetch holidays (2023-2026 covers most order dates)
    holidays_results = fetch_brasil_holidays([2023, 2024, 2025, 2026], logger)
    
    duration = (datetime.now() - start_time).total_seconds()
    log_ingestion_summary(logger, olist_results, holidays_results, duration)
    
    all_success = olist_success and len(holidays_results) > 0
    
    if not all_success:
        logger.error("INGESTION FAILED: One or more sources incomplete or unreachable")
    
    return all_success, olist_results, holidays_results


if __name__ == "__main__":
    success, olist, holidays = run_ingestion()
    exit(0 if success else 1)
