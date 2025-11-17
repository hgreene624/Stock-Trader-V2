"""
Optimization Results Tracker

Tracks and manages optimization experiment results across runs.
Provides a central leaderboard and comparison system.
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import duckdb


class OptimizationTracker:
    """
    Central tracking system for optimization experiments.

    Maintains:
    - Leaderboard of all-time best parameters
    - History of all optimization runs
    - Comparison across experiments
    """

    def __init__(self, db_path: str = "results/optimization_tracker.db"):
        """
        Initialize optimization tracker.

        Args:
            db_path: Path to DuckDB database for results storage
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(str(self.db_path))
        self._create_tables()

    def _create_tables(self):
        """Create database tables if they don't exist."""
        # Experiments table
        self.conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS experiments_id_seq;
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER DEFAULT nextval('experiments_id_seq'),
                name VARCHAR,
                method VARCHAR,  -- grid, random, evolutionary
                timestamp TIMESTAMP,
                model VARCHAR,
                backtest_period VARCHAR,
                total_runs INTEGER,
                best_metric DOUBLE,
                metric_name VARCHAR
            )
        """)

        # Results table (one row per parameter set tested)
        self.conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS results_id_seq;
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER DEFAULT nextval('results_id_seq'),
                experiment_id INTEGER,
                parameters JSON,  -- Full parameter set as JSON
                cagr DOUBLE,
                sharpe_ratio DOUBLE,
                max_drawdown DOUBLE,
                total_return DOUBLE,
                win_rate DOUBLE,
                bps DOUBLE,
                total_trades INTEGER,
                final_nav DOUBLE,
                validation_period VARCHAR,  -- in-sample, out-of-sample, or full
                notes VARCHAR
            )
        """)

        # Leaderboard view (best results across all experiments)
        self.conn.execute("""
            CREATE OR REPLACE VIEW leaderboard AS
            SELECT
                r.*,
                e.name as experiment_name,
                e.method,
                e.timestamp,
                e.model
            FROM results r
            JOIN experiments e ON r.experiment_id = e.id
            ORDER BY r.bps DESC
        """)

    def log_experiment(
        self,
        name: str,
        method: str,
        model: str,
        backtest_period: str,
        total_runs: int,
        best_metric: float,
        metric_name: str = "bps"
    ) -> int:
        """
        Log a new optimization experiment.

        Returns:
            experiment_id for logging results
        """
        result = self.conn.execute("""
            INSERT INTO experiments (name, method, timestamp, model, backtest_period, total_runs, best_metric, metric_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
        """, [
            name,
            method,
            datetime.now(),
            model,
            backtest_period,
            total_runs,
            best_metric,
            metric_name
        ]).fetchone()

        return result[0]

    def log_result(
        self,
        experiment_id: int,
        parameters: Dict[str, Any],
        metrics: Dict[str, float],
        validation_period: str = "in-sample",
        notes: str = ""
    ):
        """
        Log a single parameter set result.

        Args:
            experiment_id: ID from log_experiment
            parameters: Parameter set tested
            metrics: Performance metrics (must include cagr, sharpe_ratio, max_drawdown, etc.)
            validation_period: "in-sample", "out-of-sample", or "full"
            notes: Optional notes
        """
        self.conn.execute("""
            INSERT INTO results (
                experiment_id, parameters, cagr, sharpe_ratio, max_drawdown,
                total_return, win_rate, bps, total_trades, final_nav,
                validation_period, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            experiment_id,
            json.dumps(parameters),
            metrics.get('cagr', 0.0),
            metrics.get('sharpe_ratio', 0.0),
            metrics.get('max_drawdown', 0.0),
            metrics.get('total_return', 0.0),
            metrics.get('win_rate', 0.0),
            metrics.get('bps', 0.0),
            metrics.get('total_trades', 0),
            metrics.get('final_nav', 0.0),
            validation_period,
            notes
        ])

    def get_leaderboard(self, limit: int = 20, metric: str = "bps") -> pd.DataFrame:
        """
        Get top N results across all experiments.

        Args:
            limit: Number of results to return
            metric: Metric to sort by (bps, cagr, sharpe_ratio, etc.)

        Returns:
            DataFrame with top results
        """
        query = f"""
            SELECT
                r.id,
                e.name as experiment,
                e.method,
                e.timestamp,
                r.parameters,
                r.cagr,
                r.sharpe_ratio,
                r.max_drawdown,
                r.bps,
                r.validation_period
            FROM results r
            JOIN experiments e ON r.experiment_id = e.id
            ORDER BY r.{metric} DESC
            LIMIT ?
        """
        return self.conn.execute(query, [limit]).df()

    def get_experiment_results(self, experiment_name: str) -> pd.DataFrame:
        """Get all results for a specific experiment."""
        query = """
            SELECT
                r.*,
                e.name as experiment_name
            FROM results r
            JOIN experiments e ON r.experiment_id = e.id
            WHERE e.name = ?
            ORDER BY r.bps DESC
        """
        return self.conn.execute(query, [experiment_name]).df()

    def compare_experiments(self, experiment_names: List[str]) -> pd.DataFrame:
        """Compare best results across multiple experiments."""
        placeholders = ','.join(['?' for _ in experiment_names])
        query = f"""
            WITH best_per_experiment AS (
                SELECT
                    e.name as experiment,
                    MAX(r.bps) as best_bps,
                    MAX(r.cagr) as best_cagr,
                    MAX(r.sharpe_ratio) as best_sharpe
                FROM results r
                JOIN experiments e ON r.experiment_id = e.id
                WHERE e.name IN ({placeholders})
                GROUP BY e.name
            )
            SELECT * FROM best_per_experiment
            ORDER BY best_bps DESC
        """
        return self.conn.execute(query, experiment_names).df()

    def export_best_parameters(self, experiment_name: str, output_path: str):
        """
        Export best parameters from an experiment to a JSON file.

        Useful for creating profiles from optimization results.
        """
        query = """
            SELECT r.parameters, r.cagr, r.sharpe_ratio, r.bps
            FROM results r
            JOIN experiments e ON r.experiment_id = e.id
            WHERE e.name = ?
            ORDER BY r.bps DESC
            LIMIT 1
        """
        result = self.conn.execute(query, [experiment_name]).fetchone()

        if result:
            params = json.loads(result[0])
            export_data = {
                'experiment': experiment_name,
                'parameters': params,
                'metrics': {
                    'cagr': result[1],
                    'sharpe_ratio': result[2],
                    'bps': result[3]
                }
            }

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2)

            print(f"✓ Best parameters exported to: {output_path}")
        else:
            print(f"✗ No results found for experiment: {experiment_name}")

    def close(self):
        """Close database connection."""
        self.conn.close()
