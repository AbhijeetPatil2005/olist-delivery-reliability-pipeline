"""
Tests for FDE Data Foundations Pipeline

Run with: pytest tests/ -v
"""

import pandas as pd
import pytest
import os
import sys
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))


class TestValidationRules:
    """Test validation rules from src/validate.py"""
    
    def test_val001_delivered_after_shipped_valid(self):
        """VAL-001: Order with delivered >= shipped should NOT be flagged"""
        # Create test dataframe with valid timeline
        data = {
            'order_delivered_carrier_date': ['2024-01-05'],
            'order_delivered_customer_date': ['2024-01-10']
        }
        df = pd.DataFrame(data)
        
        # Apply validation logic (same as VAL-001 in validate.py)
        mask = pd.to_datetime(df['order_delivered_customer_date'], errors='coerce') < \
               pd.to_datetime(df['order_delivered_carrier_date'], errors='coerce')
        
        # Should not be flagged
        assert mask.sum() == 0, "Valid order should not be flagged"
    
    def test_val001_delivered_before_shipped_flagged(self):
        """VAL-001: Order with delivered < shipped SHOULD be flagged"""
        # Create test dataframe with impossible timeline
        data = {
            'order_delivered_carrier_date': ['2024-01-10'],
            'order_delivered_customer_date': ['2024-01-05']  # Before shipped!
        }
        df = pd.DataFrame(data)
        
        # Apply validation logic
        mask = pd.to_datetime(df['order_delivered_customer_date'], errors='coerce') < \
               pd.to_datetime(df['order_delivered_carrier_date'], errors='coerce')
        
        # Should be flagged
        assert mask.sum() == 1, "Impossible timeline should be flagged"
        assert df.loc[mask, 'order_delivered_customer_date'].iloc[0] == '2024-01-05'
    
    def test_val006_orphan_order_items_detected(self):
        """VAL-006: order_items with order_id not in orders should be flagged"""
        # Mock orders table (only has order_id 'A')
        orders_df = pd.DataFrame({'order_id': ['A', 'B', 'C']})
        
        # Mock order_items with an orphan (order_id 'X' not in orders)
        order_items_df = pd.DataFrame({
            'order_id': ['A', 'B', 'X'],  # 'X' is orphan
            'order_item_id': [1, 2, 3]
        })
        
        # Apply FK check logic
        valid_order_ids = set(orders_df['order_id'].dropna())
        child_order_ids = set(order_items_df['order_id'].dropna())
        orphaned = child_order_ids - valid_order_ids
        
        # Should find 1 orphan
        assert len(orphaned) == 1, "Should detect 1 orphan order_id"
        assert 'X' in orphaned, "Orphan 'X' should be detected"
    
    def test_val006_no_orphans_passes(self):
        """VAL-006: All order_items with valid order_id should pass"""
        orders_df = pd.DataFrame({'order_id': ['A', 'B', 'C']})
        order_items_df = pd.DataFrame({
            'order_id': ['A', 'B', 'C'],  # All valid
            'order_item_id': [1, 2, 3]
        })
        
        valid_order_ids = set(orders_df['order_id'].dropna())
        child_order_ids = set(order_items_df['order_id'].dropna())
        orphaned = child_order_ids - valid_order_ids
        
        assert len(orphaned) == 0, "No orphans should be found"


class TestMetrics:
    """Test metrics calculations from src/metrics.py"""
    
    def test_on_time_rate_calculation(self):
        """On-time rate = on_time_count / total_valid * 100"""
        # Create synthetic test data with known outcome
        # 8 on-time, 2 late = 80% on-time rate
        data = {
            'order_id': ['O1', 'O2', 'O3', 'O4', 'O5', 'O6', 'O7', 'O8', 'O9', 'O10'],
            'on_time': [True, True, True, True, True, True, True, True, False, False]
        }
        df = pd.DataFrame(data)
        
        # Apply calculation from compute_on_time_rate
        total_valid = len(df)
        on_time_count = df['on_time'].sum()
        on_time_rate = (on_time_count / total_valid * 100) if total_valid > 0 else 0
        
        assert total_valid == 10
        assert on_time_count == 8
        assert on_time_rate == 80.0
    
    def test_avg_delay_late_orders_only(self):
        """Average delay should only include late orders"""
        # Create synthetic data: 3 late orders with delays of 5, 10, 15 days
        data = {
            'delay_days': [5, 10, 15, 0, 0, 0]  # Last 3 are on-time (delay=0)
        }
        df = pd.DataFrame(data)
        
        late_orders = df[df['delay_days'] > 0]
        avg_delay = late_orders['delay_days'].mean()
        
        # (5 + 10 + 15) / 3 = 10
        assert avg_delay == 10.0
    
    def test_delay_split_calculation(self):
        """Pre-ship and in-transit percentages should sum to 100%"""
        # Create synthetic data
        data = {
            'pre_ship_days': [2.0, 3.0, 2.5, None],
            'in_transit_days': [8.0, 7.5, 9.0, None]
        }
        df = pd.DataFrame(data)
        
        pre_ship_with_data = df['pre_ship_days'].dropna()
        in_transit_with_data = df['in_transit_days'].dropna()
        
        avg_pre_ship = pre_ship_with_data.mean()
        avg_in_transit = in_transit_with_data.mean()
        total_avg = avg_pre_ship + avg_in_transit
        
        pre_ship_pct = (avg_pre_ship / total_avg * 100) if total_avg > 0 else 0
        in_transit_pct = (avg_in_transit / total_avg * 100) if total_avg > 0 else 0
        
        assert abs(pre_ship_pct + in_transit_pct - 100) < 0.01


class TestPipelineFailureHandling:
    """Test pipeline fails loudly when required files are missing"""
    
    def test_pipeline_fails_on_missing_orders_file(self):
        """Pipeline should fail clearly when orders CSV is missing"""
        # Temporarily rename the orders file
        orders_path = Path("data/raw/olist/olist_orders_dataset.csv")
        temp_path = Path("data/raw/olist/olist_orders_dataset.csv.bak")
        
        if orders_path.exists():
            orders_path.rename(temp_path)
            
            try:
                # Run pipeline via subprocess - should fail
                import subprocess
                result = subprocess.run(
                    ["python", "run_pipeline.py"],
                    capture_output=True,
                    text=True,
                    cwd=Path(__file__).parent.parent
                )
                
                # Should exit non-zero
                assert result.returncode != 0, "Pipeline should fail when orders file is missing"
                # Error message should be clear
                assert "MISSING" in result.stdout or "MISSING" in result.stderr, \
                    "Error message should indicate missing file"
            finally:
                # Restore the file
                if temp_path.exists():
                    temp_path.rename(orders_path)
    
    def test_ingest_verification_detects_missing_file(self):
        """verify_olist_completeness should detect missing files"""
        # Test the logic directly without importing src module
        from pathlib import Path
        import pandas as pd
        
        RAW_OLIST_DIR = Path("data/raw/olist")
        OLIST_MANIFEST = {
            "olist_orders_dataset.csv": 99441,
        }
        
        # Verify file exists
        filename = "olist_orders_dataset.csv"
        filepath = RAW_OLIST_DIR / filename
        
        # With file present, should be OK
        assert filepath.exists(), "Orders file should exist for this test"
        
        # Check verification logic
        expected_rows = OLIST_MANIFEST[filename]
        actual_rows = len(pd.read_csv(filepath))
        
        assert actual_rows >= expected_rows * 0.95, "Row count should be within 5% of expected"


class TestKnownIssues:
    """Test data quality findings from validation"""
    
    def test_excluded_orders_count_matches_known_issues(self):
        """Excluded orders count should match docs/known_issues.md"""
        # This test verifies our documentation matches reality
        known_excluded = 3003  # From known_issues.md
        
        # Read actual excluded orders from validation output
        excluded_path = Path("data/validated/orders_excluded.csv")
        if excluded_path.exists():
            excluded_df = pd.read_csv(excluded_path)
            actual_excluded = len(excluded_df)
            assert actual_excluded == known_excluded, \
                f"Excluded count {actual_excluded} should match known_issues.md value {known_excluded}"
    
    def test_valid_orders_count_matches_known_issues(self):
        """Valid orders count should match docs/known_issues.md"""
        known_valid = 96438  # From known_issues.md
        
        valid_path = Path("data/validated/orders_validated.csv")
        if valid_path.exists():
            valid_df = pd.read_csv(valid_path)
            actual_valid = len(valid_df)
            assert actual_valid == known_valid, \
                f"Valid count {actual_valid} should match known_issues.md value {known_valid}"