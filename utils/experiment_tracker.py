"""
Experiment Tracking System

Simple system for agents to log experiments, hypotheses, and results.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


class ExperimentTracker:
    """
    Track experiments for learning and iteration.

    Logs:
    - What was tried
    - Why it was tried (hypothesis)
    - What changed from baseline
    - Results
    - Conclusion and next steps
    """

    def __init__(self, log_file: str = ".experiments/experiments.jsonl"):
        """
        Initialize experiment tracker.

        Args:
            log_file: Path to experiment log file (JSONL format)
        """
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log_experiment(
        self,
        name: str,
        hypothesis: str,
        changes: Dict[str, any],
        results: Dict[str, float],
        baseline_results: Optional[Dict[str, float]] = None,
        conclusion: str = "",
        next_steps: str = ""
    ):
        """
        Log an experiment.

        Args:
            name: Experiment name (e.g., "sector_rotation_fast_momentum")
            hypothesis: Why you're trying this (e.g., "Shorter momentum will capture trends faster")
            changes: What changed vs baseline (e.g., {"momentum_period": "126 -> 90"})
            results: Key metrics (e.g., {"cagr": 0.1321, "sharpe": 1.45})
            baseline_results: Baseline metrics for comparison
            conclusion: What you learned
            next_steps: What to try next
        """
        experiment = {
            "timestamp": datetime.now().isoformat(),
            "name": name,
            "hypothesis": hypothesis,
            "changes": changes,
            "results": results,
            "baseline_results": baseline_results,
            "conclusion": conclusion,
            "next_steps": next_steps
        }

        # Append to JSONL file
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(experiment) + '\n')

        print(f"✅ Logged experiment: {name}")

    def get_experiments(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Get all experiments, optionally limited to most recent N.

        Args:
            limit: Maximum number of experiments to return (None = all)

        Returns:
            List of experiment dicts
        """
        if not self.log_file.exists():
            return []

        experiments = []
        with open(self.log_file) as f:
            for line in f:
                experiments.append(json.loads(line))

        if limit:
            return experiments[-limit:]
        return experiments

    def print_summary(self, limit: int = 10):
        """
        Print summary of recent experiments.

        Args:
            limit: Number of recent experiments to show
        """
        experiments = self.get_experiments(limit=limit)

        if not experiments:
            print("No experiments logged yet.")
            return

        print("\n" + "=" * 80)
        print(f"EXPERIMENT HISTORY (Last {len(experiments)})")
        print("=" * 80 + "\n")

        for exp in experiments:
            print(f"📊 {exp['name']}")
            print(f"   Date: {exp['timestamp']}")
            print(f"   Hypothesis: {exp['hypothesis']}")
            print(f"   Changes:")
            for key, value in exp['changes'].items():
                print(f"     {key}: {value}")
            print(f"   Results:")
            for key, value in exp['results'].items():
                print(f"     {key}: {value}")
            if exp.get('conclusion'):
                print(f"   Conclusion: {exp['conclusion']}")
            if exp.get('next_steps'):
                print(f"   Next: {exp['next_steps']}")
            print()

        print("=" * 80 + "\n")

    def get_best_result(self, metric: str = "cagr") -> Optional[Dict]:
        """
        Get experiment with best result for a given metric.

        Args:
            metric: Metric to optimize (e.g., "cagr", "sharpe")

        Returns:
            Best experiment dict or None
        """
        experiments = self.get_experiments()
        if not experiments:
            return None

        # Filter experiments that have the metric
        valid_experiments = [
            exp for exp in experiments
            if metric in exp.get('results', {})
        ]

        if not valid_experiments:
            return None

        return max(valid_experiments, key=lambda x: x['results'][metric])


# CLI interface for experiment tracking
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Experiment Tracking CLI")
    subparsers = parser.add_subparsers(dest='command')

    # Log experiment
    log_parser = subparsers.add_parser('log', help='Log an experiment')
    log_parser.add_argument('--name', required=True, help='Experiment name')
    log_parser.add_argument('--hypothesis', required=True, help='Why are you trying this?')
    log_parser.add_argument('--changes', required=True, help='What changed (JSON dict)')
    log_parser.add_argument('--results', required=True, help='Results (JSON dict)')
    log_parser.add_argument('--baseline', help='Baseline results (JSON dict)')
    log_parser.add_argument('--conclusion', default='', help='What did you learn?')
    log_parser.add_argument('--next', dest='next_steps', default='', help='What to try next?')

    # List experiments
    list_parser = subparsers.add_parser('list', help='List recent experiments')
    list_parser.add_argument('--limit', type=int, default=10, help='Number to show')

    # Get best
    best_parser = subparsers.add_parser('best', help='Show best experiment')
    best_parser.add_argument('--metric', default='cagr', help='Metric to optimize')

    args = parser.parse_args()
    tracker = ExperimentTracker()

    if args.command == 'log':
        tracker.log_experiment(
            name=args.name,
            hypothesis=args.hypothesis,
            changes=json.loads(args.changes),
            results=json.loads(args.results),
            baseline_results=json.loads(args.baseline) if args.baseline else None,
            conclusion=args.conclusion,
            next_steps=args.next_steps
        )

    elif args.command == 'list':
        tracker.print_summary(limit=args.limit)

    elif args.command == 'best':
        best = tracker.get_best_result(metric=args.metric)
        if best:
            print(f"\n🏆 Best {args.metric}: {best['name']}")
            print(f"   {args.metric.upper()}: {best['results'][args.metric]}")
            print(f"   Hypothesis: {best['hypothesis']}")
        else:
            print(f"No experiments with {args.metric} metric found.")
