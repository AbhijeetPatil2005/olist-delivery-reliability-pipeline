#!/usr/bin/env python3
"""
Olist Delivery Reliability Pipeline — Entry Point

Single command to run: ingest → validate → transform/model → metrics

Usage:
    python run_pipeline.py

Output:
    - Logs: logs/pipeline_{timestamp}.log
    - Evidence table: data/modeled/output/metrics_evidence_table.csv
    - Summary: data/modeled/output/metrics_summary.md
"""

import sys
import logging
import traceback
from datetime import datetime
from pathlib import Path


def setup_main_logging() -> logging.Logger:
    """Configure root logging for the pipeline."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = Path("logs") / f"pipeline_{timestamp}.log"
    
    logger = logging.getLogger("pipeline")
    logger.setLevel(logging.INFO)
    
    # File handler
    file_handler = logging.FileHandler(log_filename, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger, log_filename


def print_banner(logger: logging.Logger) -> None:
    """Print pipeline start banner."""
    banner = """
======================================================================
   OLIST DELIVERY RELIABILITY PIPELINE — FDE DATA FOUNDATIONS
======================================================================
   Stage 1: INGEST     -> Raw CSV files + Brazil holidays API
   Stage 2: VALIDATE   -> Profile tables, apply validation rules
   Stage 3: TRANSFORM  -> Reconstruct events, calculate outcomes
   Stage 4: METRICS    -> 5 delivery reliability KPIs
======================================================================
    """.strip()
    logger.info(banner)


def run_pipeline() -> bool:
    """
    Execute the full pipeline.
    
    Returns:
        True if pipeline succeeded, False otherwise
    """
    start_time = datetime.now()
    logger, log_filename = setup_main_logging()
    
    print_banner(logger)
    
    stages = [
        ("INGEST", "src.ingest", "run_ingestion"),
        ("VALIDATE", "src.validate", "run_validation"),
        ("TRANSFORM", "src.transform_model", "run_transform"),
        ("METRICS", "src.metrics", "run_metrics"),
    ]
    
    stage_times = {}
    
    for stage_name, module_name, func_name in stages:
        stage_start = datetime.now()
        
        logger.info("")
        logger.info("=" * 70)
        logger.info(f"STAGE: {stage_name}")
        logger.info("=" * 70)
        
        try:
            module = __import__(module_name, fromlist=[func_name])
            func = getattr(module, func_name)
            success = func()
            
            if not success:
                logger.error("")
                logger.error(f"[X] STAGE {stage_name} FAILED")
                logger.error(f"Check logs in: logs/")
                return False
            
            stage_duration = (datetime.now() - stage_start).total_seconds()
            stage_times[stage_name] = stage_duration
            logger.info(f"[OK] Stage {stage_name} completed in {stage_duration:.2f}s")
            
        except ImportError as e:
            logger.error(f"[X] Failed to import {module_name}: {e}")
            logger.error(f"Ensure all src/*.py files exist and dependencies are installed")
            return False
        except Exception as e:
            logger.error(f"[X] Stage {stage_name} crashed with exception:")
            logger.error(traceback.format_exc())
            return False
    
    # Final summary
    total_duration = (datetime.now() - start_time).total_seconds()
    
    logger.info("")
    logger.info("=" * 70)
    logger.info("PIPELINE COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Total duration: {total_duration:.2f}s")
    logger.info("")
    logger.info("Stage breakdown:")
    for stage, duration in stage_times.items():
        logger.info(f"  - {stage}: {duration:.2f}s")
    logger.info("")
    logger.info("Output files:")
    logger.info("  [EVIDENCE] data/modeled/output/metrics_evidence_table.csv")
    logger.info("  [SUMMARY]  data/modeled/output/metrics_summary.md")
    logger.info("  [LOGS]     logs/pipeline_*.log")
    logger.info("")
    logger.info("=" * 70)
    
    return True


if __name__ == "__main__":
    success = run_pipeline()
    sys.exit(0 if success else 1)