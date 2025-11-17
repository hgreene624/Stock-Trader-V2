"""
Optimization Reporting Module

Generate comparison reports and visualizations for optimization experiments.

Features:
- Side-by-side experiment comparison
- Parameter distribution analysis
- Performance metric rankings
- Top N parameter sets per experiment
- Export to CSV, HTML, and JSON formats
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict


class OptimizationReporter:
    """
    Generate reports comparing optimization experiment results.

    Can compare multiple experiments using different methods (grid, random, EA)
    and visualize parameter space exploration and performance.
    """

    def __init__(self):
        """Initialize reporter."""
        self.experiments = {}

    def load_experiment_results(self, experiment_name: str, results_path: str):
        """
        Load experiment results from JSON file.

        Args:
            experiment_name: Name to identify this experiment
            results_path: Path to results JSON file

        Note: In production, this would load from DuckDB database
        """
        results_file = Path(results_path)

        if not results_file.exists():
            raise FileNotFoundError(f"Results file not found: {results_path}")

        with open(results_file) as f:
            data = json.load(f)

        self.experiments[experiment_name] = data

        print(f"Loaded experiment: {experiment_name}")
        print(f"  Method: {data.get('method', 'unknown')}")
        print(f"  Parameter sets: {len(data.get('parameter_sets', []))}")

    def generate_summary_table(self) -> List[Dict[str, Any]]:
        """
        Generate summary comparison table.

        Returns:
            List of summary rows, one per experiment
        """
        summary = []

        for exp_name, exp_data in self.experiments.items():
            row = {
                'experiment': exp_name,
                'method': exp_data.get('method', 'unknown'),
                'num_parameter_sets': len(exp_data.get('parameter_sets', [])),
                'timestamp': exp_data.get('timestamp', 'unknown')
            }

            # Add performance metrics if available
            results = exp_data.get('results', [])
            if results:
                # Calculate aggregate statistics
                metrics = ['bps', 'sharpe_ratio', 'cagr', 'max_drawdown']
                for metric in metrics:
                    values = [r.get(metric) for r in results if r.get(metric) is not None]
                    if values:
                        row[f'{metric}_best'] = max(values) if metric != 'max_drawdown' else min(values)
                        row[f'{metric}_mean'] = sum(values) / len(values)
                        row[f'{metric}_worst'] = min(values) if metric != 'max_drawdown' else max(values)

            summary.append(row)

        return summary

    def generate_top_n_report(self, n: int = 10) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate top N parameter sets per experiment.

        Args:
            n: Number of top performers to include

        Returns:
            Dict mapping experiment name to top N parameter sets
        """
        top_n_report = {}

        for exp_name, exp_data in self.experiments.items():
            parameter_sets = exp_data.get('parameter_sets', [])
            results = exp_data.get('results', [])

            # If results are available, sort by BPS (or other metric)
            if results:
                # Combine parameters with results
                combined = [
                    {**params, **result}
                    for params, result in zip(parameter_sets, results)
                ]

                # Sort by BPS (descending)
                combined.sort(key=lambda x: x.get('bps', 0), reverse=True)

                # Take top N
                top_n_report[exp_name] = combined[:n]
            else:
                # No results yet, just include first N parameter sets
                top_n_report[exp_name] = parameter_sets[:n]

        return top_n_report

    def generate_parameter_distribution_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Analyze parameter distributions across experiments.

        Returns:
            Dict mapping experiment to parameter statistics
        """
        stats = {}

        for exp_name, exp_data in self.experiments.items():
            parameter_sets = exp_data.get('parameter_sets', [])

            if not parameter_sets:
                continue

            # Get all parameter names
            param_names = set()
            for pset in parameter_sets:
                param_names.update(pset.keys())

            # Calculate statistics per parameter
            param_stats = {}
            for param in param_names:
                values = [pset.get(param) for pset in parameter_sets if param in pset]

                if not values:
                    continue

                # Check if numeric
                if all(isinstance(v, (int, float)) for v in values):
                    param_stats[param] = {
                        'min': min(values),
                        'max': max(values),
                        'mean': sum(values) / len(values),
                        'unique_values': len(set(values)),
                        'total_samples': len(values)
                    }
                else:
                    # Categorical parameter
                    param_stats[param] = {
                        'unique_values': len(set(str(v) for v in values)),
                        'total_samples': len(values),
                        'values': list(set(str(v) for v in values))
                    }

            stats[exp_name] = param_stats

        return stats

    def generate_comparison_report(
        self,
        output_path: str,
        top_n: int = 10,
        format: str = 'txt'
    ):
        """
        Generate comprehensive comparison report.

        Args:
            output_path: Path to save report
            top_n: Number of top performers to include
            format: Output format ('txt', 'json', 'html')
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        if format == 'txt':
            self._generate_text_report(output_file, top_n)
        elif format == 'json':
            self._generate_json_report(output_file, top_n)
        elif format == 'html':
            self._generate_html_report(output_file, top_n)
        else:
            raise ValueError(f"Unknown format: {format}")

        print(f"\n✓ Report saved to: {output_file}")

    def _generate_text_report(self, output_file: Path, top_n: int):
        """Generate plain text report."""
        lines = []

        # Header
        lines.append("=" * 100)
        lines.append("OPTIMIZATION EXPERIMENT COMPARISON REPORT")
        lines.append("=" * 100)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Experiments: {len(self.experiments)}")
        lines.append("")

        # Summary table
        lines.append("-" * 100)
        lines.append("SUMMARY")
        lines.append("-" * 100)
        summary = self.generate_summary_table()
        for row in summary:
            lines.append(f"\nExperiment: {row['experiment']}")
            lines.append(f"  Method: {row['method']}")
            lines.append(f"  Parameter sets: {row['num_parameter_sets']}")
            lines.append(f"  Timestamp: {row['timestamp']}")

            # Performance metrics if available
            if 'bps_best' in row:
                lines.append(f"\n  Performance:")
                lines.append(f"    BPS (best): {row.get('bps_best', 'N/A')}")
                lines.append(f"    BPS (mean): {row.get('bps_mean', 'N/A')}")
                lines.append(f"    Sharpe (best): {row.get('sharpe_ratio_best', 'N/A')}")
                lines.append(f"    CAGR (best): {row.get('cagr_best', 'N/A')}")

        # Top N parameter sets
        lines.append("\n" + "-" * 100)
        lines.append(f"TOP {top_n} PARAMETER SETS PER EXPERIMENT")
        lines.append("-" * 100)

        top_n_report = self.generate_top_n_report(top_n)
        for exp_name, top_params in top_n_report.items():
            lines.append(f"\n{exp_name}:")
            for i, params in enumerate(top_params, 1):
                # Extract parameter values (exclude metadata like bps, sharpe, etc.)
                param_strs = []
                for key, value in params.items():
                    if key not in ['bps', 'sharpe_ratio', 'cagr', 'max_drawdown', 'win_rate']:
                        if isinstance(value, float):
                            param_strs.append(f"{key}={value:.2f}")
                        else:
                            param_strs.append(f"{key}={value}")

                lines.append(f"  {i}. {', '.join(param_strs)}")

                # Show performance if available
                if 'bps' in params:
                    lines.append(f"     → BPS={params.get('bps', 'N/A')}, "
                               f"Sharpe={params.get('sharpe_ratio', 'N/A')}, "
                               f"CAGR={params.get('cagr', 'N/A')}")

        # Parameter distribution statistics
        lines.append("\n" + "-" * 100)
        lines.append("PARAMETER DISTRIBUTION STATISTICS")
        lines.append("-" * 100)

        param_stats = self.generate_parameter_distribution_stats()
        for exp_name, stats in param_stats.items():
            lines.append(f"\n{exp_name}:")
            for param, stat_dict in stats.items():
                lines.append(f"\n  {param}:")
                for stat_name, stat_value in stat_dict.items():
                    if isinstance(stat_value, float):
                        lines.append(f"    {stat_name}: {stat_value:.2f}")
                    elif isinstance(stat_value, list):
                        lines.append(f"    {stat_name}: {', '.join(map(str, stat_value[:5]))}")
                    else:
                        lines.append(f"    {stat_name}: {stat_value}")

        # Footer
        lines.append("\n" + "=" * 100)
        lines.append("END OF REPORT")
        lines.append("=" * 100)

        # Write to file
        with open(output_file, 'w') as f:
            f.write('\n'.join(lines))

    def _generate_json_report(self, output_file: Path, top_n: int):
        """Generate JSON report."""
        report = {
            'generated_at': datetime.now().isoformat(),
            'num_experiments': len(self.experiments),
            'summary': self.generate_summary_table(),
            'top_n_per_experiment': self.generate_top_n_report(top_n),
            'parameter_statistics': self.generate_parameter_distribution_stats()
        }

        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

    def _generate_html_report(self, output_file: Path, top_n: int):
        """Generate HTML report."""
        # Simple HTML template
        html = []
        html.append("<!DOCTYPE html>")
        html.append("<html>")
        html.append("<head>")
        html.append("<title>Optimization Experiment Comparison</title>")
        html.append("<style>")
        html.append("body { font-family: Arial, sans-serif; margin: 20px; }")
        html.append("h1 { color: #333; }")
        html.append("h2 { color: #666; border-bottom: 2px solid #ddd; padding-bottom: 5px; }")
        html.append("table { border-collapse: collapse; width: 100%; margin: 20px 0; }")
        html.append("th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }")
        html.append("th { background-color: #4CAF50; color: white; }")
        html.append("tr:nth-child(even) { background-color: #f2f2f2; }")
        html.append(".metric { font-weight: bold; color: #4CAF50; }")
        html.append("</style>")
        html.append("</head>")
        html.append("<body>")

        html.append("<h1>Optimization Experiment Comparison Report</h1>")
        html.append(f"<p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>")
        html.append(f"<p>Experiments: {len(self.experiments)}</p>")

        # Summary table
        html.append("<h2>Summary</h2>")
        html.append("<table>")
        html.append("<tr><th>Experiment</th><th>Method</th><th>Parameter Sets</th><th>Best BPS</th></tr>")

        summary = self.generate_summary_table()
        for row in summary:
            html.append("<tr>")
            html.append(f"<td>{row['experiment']}</td>")
            html.append(f"<td>{row['method']}</td>")
            html.append(f"<td>{row['num_parameter_sets']}</td>")
            html.append(f"<td class='metric'>{row.get('bps_best', 'N/A')}</td>")
            html.append("</tr>")

        html.append("</table>")

        # Top N
        html.append(f"<h2>Top {top_n} Parameter Sets</h2>")

        top_n_report = self.generate_top_n_report(top_n)
        for exp_name, top_params in top_n_report.items():
            html.append(f"<h3>{exp_name}</h3>")
            html.append("<table>")
            html.append("<tr><th>Rank</th><th>Parameters</th><th>BPS</th></tr>")

            for i, params in enumerate(top_params, 1):
                # Extract parameters
                param_str = ", ".join(
                    f"{k}={v:.2f}" if isinstance(v, float) else f"{k}={v}"
                    for k, v in params.items()
                    if k not in ['bps', 'sharpe_ratio', 'cagr', 'max_drawdown']
                )

                html.append("<tr>")
                html.append(f"<td>{i}</td>")
                html.append(f"<td>{param_str}</td>")
                html.append(f"<td class='metric'>{params.get('bps', 'N/A')}</td>")
                html.append("</tr>")

            html.append("</table>")

        html.append("</body>")
        html.append("</html>")

        # Write to file
        with open(output_file, 'w') as f:
            f.write('\n'.join(html))


# Example usage and testing
if __name__ == "__main__":
    print("=" * 80)
    print("Optimization Reporting Module Test")
    print("=" * 80)

    # Initialize reporter
    reporter = OptimizationReporter()

    # Check if results exist
    results_dir = Path("results")
    json_files = list(results_dir.glob("*.json")) if results_dir.exists() else []

    if not json_files:
        print("\nNo experiment results found in results/ directory")
        print("Run experiments first using:")
        print("  python -m engines.optimization.cli run --experiment configs/experiments/exp_001.yaml")
        print("\nCreating mock results for demonstration...")

        # Create mock results for testing
        mock_exp1 = {
            'experiment': 'exp_001_equity_trend_grid',
            'method': 'grid',
            'timestamp': datetime.now().isoformat(),
            'parameter_sets': [
                {'slow_ma_period': 150, 'momentum_lookback_days': 30},
                {'slow_ma_period': 200, 'momentum_lookback_days': 60},
                {'slow_ma_period': 250, 'momentum_lookback_days': 90}
            ],
            'results': [
                {'bps': 0.85, 'sharpe_ratio': 1.2, 'cagr': 0.12, 'max_drawdown': -0.15},
                {'bps': 0.92, 'sharpe_ratio': 1.4, 'cagr': 0.15, 'max_drawdown': -0.12},
                {'bps': 0.78, 'sharpe_ratio': 1.1, 'cagr': 0.10, 'max_drawdown': -0.18}
            ]
        }

        results_dir.mkdir(exist_ok=True)
        with open(results_dir / "exp_001_summary.json", 'w') as f:
            json.dump(mock_exp1, f, indent=2)

        json_files = [results_dir / "exp_001_summary.json"]

    # Load all experiment results
    print(f"\nLoading {len(json_files)} experiment results...\n")
    for json_file in json_files[:3]:  # Limit to 3 for testing
        exp_name = json_file.stem
        reporter.load_experiment_results(exp_name, str(json_file))

    # Generate comparison report
    print("\nGenerating comparison reports...")

    # Text report
    reporter.generate_comparison_report(
        output_path="results/comparison_report.txt",
        top_n=5,
        format='txt'
    )

    # JSON report
    reporter.generate_comparison_report(
        output_path="results/comparison_report.json",
        top_n=5,
        format='json'
    )

    # HTML report
    reporter.generate_comparison_report(
        output_path="results/comparison_report.html",
        top_n=5,
        format='html'
    )

    print("\n" + "=" * 80)
    print("✓ Reporting module test complete")
    print("=" * 80)
