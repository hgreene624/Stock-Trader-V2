"""
Data Burn Tracker

Tracks which data periods have been used for testing to prevent data contamination.

From "Building Algorithmic Trading Systems":
"Once you've tested on a period, that data is 'burned' - you can't use it for
validation again. Keep a log of what data you've touched and when, and design
tests to use fresh data."

Usage:
    from engines.validation.data_burn import DataBurnTracker

    tracker = DataBurnTracker()

    # Record a test
    tracker.record_test(
        model_name="SectorRotationModel_v1",
        test_type="backtest",
        start_date="2020-01-01",
        end_date="2024-12-31",
        description="Initial baseline test"
    )

    # Check if period is burned
    is_burned = tracker.is_burned(
        model_name="SectorRotationModel_v1",
        start_date="2023-01-01",
        end_date="2024-12-31"
    )

    # View burn log
    tracker.print_summary()
"""

import json
from pathlib import Path
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import pandas as pd


@dataclass
class BurnRecord:
    """Record of a data burn event."""
    timestamp: str  # ISO format
    model_name: str
    test_type: str  # "backtest", "optimization", "monkey_test", "component_test", etc.
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
    description: str
    operator: str    # Who ran the test


class DataBurnTracker:
    """
    Tracks data usage to prevent contamination.

    Maintains a log of all tests run and which data periods were used.
    Warns when attempting to reuse data that has been "burned" by previous tests.
    """

    def __init__(self, log_path: Optional[str] = None):
        """
        Initialize data burn tracker.

        Args:
            log_path: Path to burn log file (default: logs/data_burn_log.jsonl)
        """
        if log_path is None:
            log_path = "logs/data_burn_log.jsonl"

        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        # Create log file if it doesn't exist
        if not self.log_path.exists():
            self.log_path.touch()

    def record_test(
        self,
        model_name: str,
        test_type: str,
        start_date: str,
        end_date: str,
        description: str,
        operator: str = "agent"
    ):
        """
        Record a test that uses data.

        Args:
            model_name: Name of model being tested
            test_type: Type of test (backtest, optimization, etc.)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            description: Brief description of test purpose
            operator: Who ran the test (default: "agent")
        """
        record = BurnRecord(
            timestamp=datetime.now().isoformat(),
            model_name=model_name,
            test_type=test_type,
            start_date=start_date,
            end_date=end_date,
            description=description,
            operator=operator
        )

        # Append to log
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(asdict(record)) + '\n')

    def is_burned(
        self,
        model_name: str,
        start_date: str,
        end_date: str,
        min_overlap_days: int = 30
    ) -> Tuple[bool, List[BurnRecord]]:
        """
        Check if a data period has been burned (used before).

        Args:
            model_name: Name of model
            start_date: Start date to check (YYYY-MM-DD)
            end_date: End date to check (YYYY-MM-DD)
            min_overlap_days: Minimum overlap to consider burned (default: 30 days)

        Returns:
            Tuple of (is_burned: bool, overlapping_records: List[BurnRecord])
        """
        # Parse dates
        test_start = pd.to_datetime(start_date)
        test_end = pd.to_datetime(end_date)

        # Read all records for this model
        records = self.get_records(model_name=model_name)

        overlapping = []
        for record in records:
            record_start = pd.to_datetime(record.start_date)
            record_end = pd.to_datetime(record.end_date)

            # Calculate overlap
            overlap_start = max(test_start, record_start)
            overlap_end = min(test_end, record_end)

            if overlap_start <= overlap_end:
                overlap_days = (overlap_end - overlap_start).days
                if overlap_days >= min_overlap_days:
                    overlapping.append(record)

        is_burned = len(overlapping) > 0
        return is_burned, overlapping

    def get_records(
        self,
        model_name: Optional[str] = None,
        test_type: Optional[str] = None,
        start_after: Optional[str] = None
    ) -> List[BurnRecord]:
        """
        Get burn records with optional filtering.

        Args:
            model_name: Filter by model name
            test_type: Filter by test type
            start_after: Filter to records after this date (YYYY-MM-DD)

        Returns:
            List of matching BurnRecord objects
        """
        if not self.log_path.exists():
            return []

        records = []
        with open(self.log_path, 'r') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    record = BurnRecord(**data)

                    # Apply filters
                    if model_name and record.model_name != model_name:
                        continue
                    if test_type and record.test_type != test_type:
                        continue
                    if start_after and record.start_date < start_after:
                        continue

                    records.append(record)

        return records

    def get_available_periods(
        self,
        model_name: str,
        full_range_start: str = "2010-01-01",
        full_range_end: Optional[str] = None,
        min_period_days: int = 365
    ) -> List[Tuple[str, str]]:
        """
        Get available (unburned) data periods for a model.

        Args:
            model_name: Name of model
            full_range_start: Start of full available data range
            full_range_end: End of full available data range (default: today)
            min_period_days: Minimum period length to consider (default: 365 days)

        Returns:
            List of (start_date, end_date) tuples for unburned periods
        """
        if full_range_end is None:
            full_range_end = date.today().isoformat()

        # Get all burned periods
        records = self.get_records(model_name=model_name)

        if not records:
            # No burns, entire range is available
            return [(full_range_start, full_range_end)]

        # Create timeline of burns
        burns = []
        for record in records:
            burns.append((
                pd.to_datetime(record.start_date),
                pd.to_datetime(record.end_date)
            ))

        # Sort by start date
        burns.sort(key=lambda x: x[0])

        # Find gaps
        full_start = pd.to_datetime(full_range_start)
        full_end = pd.to_datetime(full_range_end)

        available = []
        current = full_start

        for burn_start, burn_end in burns:
            # Check gap before this burn
            if current < burn_start:
                gap_days = (burn_start - current).days
                if gap_days >= min_period_days:
                    available.append((
                        current.strftime('%Y-%m-%d'),
                        burn_start.strftime('%Y-%m-%d')
                    ))

            # Move current pointer past this burn
            current = max(current, burn_end)

        # Check final gap
        if current < full_end:
            gap_days = (full_end - current).days
            if gap_days >= min_period_days:
                available.append((
                    current.strftime('%Y-%m-%d'),
                    full_end.strftime('%Y-%m-%d')
                ))

        return available

    def print_summary(self, model_name: Optional[str] = None):
        """
        Print summary of data burns.

        Args:
            model_name: Optional filter by model name
        """
        records = self.get_records(model_name=model_name)

        if not records:
            print("No data burns recorded.")
            return

        print(f"\n{'='*80}")
        print("DATA BURN LOG")
        if model_name:
            print(f"Model: {model_name}")
        print(f"{'='*80}\n")

        # Group by model
        by_model = {}
        for record in records:
            if record.model_name not in by_model:
                by_model[record.model_name] = []
            by_model[record.model_name].append(record)

        for model, model_records in by_model.items():
            print(f"\n{model}:")
            print(f"{'-'*80}")

            for record in model_records:
                ts = datetime.fromisoformat(record.timestamp).strftime('%Y-%m-%d %H:%M')
                print(f"  [{ts}] {record.test_type}")
                print(f"    Period: {record.start_date} to {record.end_date}")
                print(f"    Description: {record.description}")
                print(f"    Operator: {record.operator}")
                print()

        print(f"{'='*80}\n")

        # Print available periods
        if model_name:
            available = self.get_available_periods(model_name)
            if available:
                print(f"\nAvailable (unburned) periods for {model_name}:")
                for start, end in available:
                    print(f"  {start} to {end}")
            else:
                print(f"\n⚠️  No unburned periods available for {model_name}")

    def check_and_warn(
        self,
        model_name: str,
        start_date: str,
        end_date: str,
        test_type: str,
        description: str,
        operator: str = "agent",
        auto_record: bool = True
    ) -> bool:
        """
        Check if period is burned, warn if so, optionally record test.

        Args:
            model_name: Model being tested
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            test_type: Type of test
            description: Test description
            operator: Who is running test
            auto_record: Automatically record this test (default: True)

        Returns:
            True if period is clean (not burned), False if burned
        """
        is_burned, overlapping = self.is_burned(model_name, start_date, end_date)

        if is_burned:
            print(f"\n⚠️  DATA BURN WARNING")
            print(f"{'='*60}")
            print(f"Period {start_date} to {end_date} has been used before!")
            print(f"Model: {model_name}")
            print(f"\nOverlapping tests:")
            for record in overlapping:
                print(f"  - {record.test_type} on {record.start_date} to {record.end_date}")
                print(f"    Description: {record.description}")
            print(f"\n⚠️  Using burned data may lead to overfitting!")
            print(f"{'='*60}\n")

        # Record this test if requested
        if auto_record:
            self.record_test(
                model_name=model_name,
                test_type=test_type,
                start_date=start_date,
                end_date=end_date,
                description=description,
                operator=operator
            )

        return not is_burned


# Global tracker instance
_global_tracker = None


def get_tracker() -> DataBurnTracker:
    """Get global data burn tracker instance."""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = DataBurnTracker()
    return _global_tracker
