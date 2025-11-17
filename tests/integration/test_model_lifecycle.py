"""
Integration Test: Model Lifecycle Management

Tests the complete lifecycle management workflow:
1. Promote model from research → candidate → paper → live
2. Verify transitions are tracked in lifecycle state file
3. Verify events are logged to lifecycle events file
4. Verify paper runner loads only candidate/paper models
5. Verify live runner loads only live models
6. Test demotion workflow
7. Test lifecycle validation (when backtest results available)

This test ensures all lifecycle components work together correctly.
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from models.base import BaseModel, Context, ModelOutput
from live.paper_runner import PaperRunner
from live.live_runner import LiveRunner
import pandas as pd
from decimal import Decimal


class TestModel(BaseModel):
    """Test model for integration testing."""

    def generate_target_weights(self, context: Context) -> ModelOutput:
        """Return simple weights for testing."""
        return ModelOutput(
            model_name=self.name,
            timestamp=context.timestamp,
            weights={"SPY": 0.5}  # 50% of model budget
        )


class TestLifecycleIntegration:
    """Integration tests for complete lifecycle workflow."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary directory for all test files
        self.test_dir = Path(tempfile.mkdtemp())
        self.configs_dir = self.test_dir / "configs"
        self.logs_dir = self.test_dir / "logs"
        self.configs_dir.mkdir(parents=True)
        self.logs_dir.mkdir(parents=True)

        # File paths
        self.lifecycle_file = self.configs_dir / ".model_lifecycle.json"
        self.lifecycle_log = self.logs_dir / "model_lifecycle_events.jsonl"

        # Create test model
        self.model = TestModel(
            name="IntegrationTestModel",
            version="1.0.0",
            universe=["SPY"],
            lifecycle_stage="research"
        )

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def _log_lifecycle_event(self, model_name: str, from_stage: str, to_stage: str, reason: str, operator: str = "test"):
        """Helper to log lifecycle event."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "model_name": model_name,
            "from_stage": from_stage,
            "to_stage": to_stage,
            "reason": reason,
            "operator": operator
        }

        with open(self.lifecycle_log, 'a') as f:
            f.write(json.dumps(event) + '\n')

        return event

    def _update_lifecycle_state(self, model_name: str, new_stage: str):
        """Helper to update lifecycle state."""
        if self.lifecycle_file.exists():
            with open(self.lifecycle_file, 'r') as f:
                states = json.load(f)
        else:
            states = {}

        states[model_name] = new_stage

        with open(self.lifecycle_file, 'w') as f:
            json.dump(states, f, indent=2)

    def test_complete_promotion_workflow(self):
        """Test promoting model through all lifecycle stages."""
        model_name = self.model.name

        # Initial state: research
        assert self.model.lifecycle_stage == "research"

        # Promote to candidate
        self._update_lifecycle_state(model_name, "candidate")
        self._log_lifecycle_event(
            model_name,
            "research",
            "candidate",
            "Passed backtest criteria: Sharpe=1.5, CAGR=0.15",
            "test_operator"
        )

        # Verify state file
        with open(self.lifecycle_file, 'r') as f:
            states = json.load(f)
        assert states[model_name] == "candidate"

        # Verify event log
        with open(self.lifecycle_log, 'r') as f:
            events = [json.loads(line) for line in f]
        assert len(events) == 1
        assert events[0]["from_stage"] == "research"
        assert events[0]["to_stage"] == "candidate"

        # Promote to paper
        self._update_lifecycle_state(model_name, "paper")
        self._log_lifecycle_event(
            model_name,
            "candidate",
            "paper",
            "Passed validation criteria",
            "test_operator"
        )

        # Verify state file
        with open(self.lifecycle_file, 'r') as f:
            states = json.load(f)
        assert states[model_name] == "paper"

        # Verify event log
        with open(self.lifecycle_log, 'r') as f:
            events = [json.loads(line) for line in f]
        assert len(events) == 2
        assert events[1]["from_stage"] == "candidate"
        assert events[1]["to_stage"] == "paper"

        # Promote to live
        self._update_lifecycle_state(model_name, "live")
        self._log_lifecycle_event(
            model_name,
            "paper",
            "live",
            "Passed paper trading validation: 45 days, 25 trades",
            "test_operator"
        )

        # Verify final state
        with open(self.lifecycle_file, 'r') as f:
            states = json.load(f)
        assert states[model_name] == "live"

        # Verify complete event log
        with open(self.lifecycle_log, 'r') as f:
            events = [json.loads(line) for line in f]
        assert len(events) == 3
        assert events[2]["from_stage"] == "paper"
        assert events[2]["to_stage"] == "live"

        # Verify lifecycle progression
        assert events[0]["from_stage"] == "research"
        assert events[1]["from_stage"] == "candidate"
        assert events[2]["from_stage"] == "paper"
        assert events[2]["to_stage"] == "live"

    def test_demotion_workflow(self):
        """Test demoting model through lifecycle stages."""
        model_name = self.model.name

        # Start at live
        self._update_lifecycle_state(model_name, "live")

        # Demote to paper
        self._update_lifecycle_state(model_name, "paper")
        self._log_lifecycle_event(
            model_name,
            "live",
            "paper",
            "Performance degradation detected",
            "test_operator"
        )

        # Verify state
        with open(self.lifecycle_file, 'r') as f:
            states = json.load(f)
        assert states[model_name] == "paper"

        # Demote to candidate
        self._update_lifecycle_state(model_name, "candidate")
        self._log_lifecycle_event(
            model_name,
            "paper",
            "candidate",
            "Paper trading performance below threshold",
            "test_operator"
        )

        # Verify state
        with open(self.lifecycle_file, 'r') as f:
            states = json.load(f)
        assert states[model_name] == "candidate"

        # Demote to research
        self._update_lifecycle_state(model_name, "research")
        self._log_lifecycle_event(
            model_name,
            "candidate",
            "research",
            "Major strategy revision required",
            "test_operator"
        )

        # Verify final state
        with open(self.lifecycle_file, 'r') as f:
            states = json.load(f)
        assert states[model_name] == "research"

        # Verify all demotions logged
        with open(self.lifecycle_log, 'r') as f:
            events = [json.loads(line) for line in f]
        assert len(events) == 3

    def test_paper_runner_lifecycle_filtering(self):
        """Test that paper runner only loads candidate/paper models."""
        # Create multiple models at different stages
        models = [
            TestModel("Model_Research", "1.0.0", ["SPY"], lifecycle_stage="research"),
            TestModel("Model_Candidate", "1.0.0", ["QQQ"], lifecycle_stage="candidate"),
            TestModel("Model_Paper", "1.0.0", ["IWM"], lifecycle_stage="paper"),
            TestModel("Model_Live", "1.0.0", ["DIA"], lifecycle_stage="live")
        ]

        # Set lifecycle states
        lifecycle_states = {
            "Model_Research": "research",
            "Model_Candidate": "candidate",
            "Model_Paper": "paper",
            "Model_Live": "live"
        }

        with open(self.lifecycle_file, 'w') as f:
            json.dump(lifecycle_states, f)

        # Create minimal config
        config = {
            "paper_trading": {},
            "models": {
                "Model_Research": {"budget": 0.25},
                "Model_Candidate": {"budget": 0.25},
                "Model_Paper": {"budget": 0.25},
                "Model_Live": {"budget": 0.25}
            },
            "risk": {},
            "data": {},
            "regime": {}
        }

        config_path = self.configs_dir / "test_config.yaml"
        import yaml
        with open(config_path, 'w') as f:
            yaml.dump(config, f)

        # Create paper runner
        # Temporarily change lifecycle file path for testing
        import live.paper_runner as pr_module
        original_lifecycle_file = pr_module

        try:
            # Create runner
            runner = PaperRunner(str(config_path))

            # Manually set lifecycle file path for testing
            runner.lifecycle_file = self.lifecycle_file

            # Filter models
            filtered = runner.filter_models_by_lifecycle(models)

            # Verify only candidate and paper models included
            assert len(filtered) == 2
            filtered_names = [m.name for m in filtered]
            assert "Model_Candidate" in filtered_names
            assert "Model_Paper" in filtered_names
            assert "Model_Research" not in filtered_names
            assert "Model_Live" not in filtered_names

        finally:
            pass

    def test_live_runner_lifecycle_filtering(self):
        """Test that live runner only loads live models."""
        # Create multiple models at different stages
        models = [
            TestModel("Model_Research", "1.0.0", ["SPY"], lifecycle_stage="research"),
            TestModel("Model_Candidate", "1.0.0", ["QQQ"], lifecycle_stage="candidate"),
            TestModel("Model_Paper", "1.0.0", ["IWM"], lifecycle_stage="paper"),
            TestModel("Model_Live", "1.0.0", ["DIA"], lifecycle_stage="live")
        ]

        # Set lifecycle states
        lifecycle_states = {
            "Model_Research": "research",
            "Model_Candidate": "candidate",
            "Model_Paper": "paper",
            "Model_Live": "live"
        }

        with open(self.lifecycle_file, 'w') as f:
            json.dump(lifecycle_states, f)

        # Create minimal config (with kill_switch disabled)
        config = {
            "live_trading": {"kill_switch": False},
            "models": {
                "Model_Research": {"budget": 0.25},
                "Model_Candidate": {"budget": 0.25},
                "Model_Paper": {"budget": 0.25},
                "Model_Live": {"budget": 0.25}
            },
            "risk": {},
            "data": {},
            "regime": {}
        }

        config_path = self.configs_dir / "test_config.yaml"
        import yaml
        with open(config_path, 'w') as f:
            yaml.dump(config, f)

        # Create live runner
        runner = LiveRunner(str(config_path))

        # Manually set lifecycle file path for testing
        runner.lifecycle_file = self.lifecycle_file

        # Filter models
        filtered = runner.filter_models_by_lifecycle(models)

        # Verify only live models included
        assert len(filtered) == 1
        assert filtered[0].name == "Model_Live"

    def test_live_runner_kill_switch(self):
        """Test that live runner respects kill switch."""
        # Create config with kill_switch enabled
        config = {
            "live_trading": {"kill_switch": True},
            "models": {},
            "risk": {}
        }

        config_path = self.configs_dir / "test_config.yaml"
        import yaml
        with open(config_path, 'w') as f:
            yaml.dump(config, f)

        # Attempt to create live runner
        with pytest.raises(RuntimeError, match="KILL SWITCH ACTIVATED"):
            LiveRunner(str(config_path))

    def test_lifecycle_state_file_missing_live_runner(self):
        """Test that live runner raises error if lifecycle state file missing."""
        # Create config
        config = {
            "live_trading": {"kill_switch": False},
            "models": {},
            "risk": {}
        }

        config_path = self.configs_dir / "test_config.yaml"
        import yaml
        with open(config_path, 'w') as f:
            yaml.dump(config, f)

        # Create runner
        runner = LiveRunner(str(config_path))

        # Set lifecycle file to non-existent path
        runner.lifecycle_file = self.test_dir / "nonexistent.json"

        # Attempt to load lifecycle states
        with pytest.raises(FileNotFoundError, match="No lifecycle state file found"):
            runner.load_lifecycle_states()

    def test_multiple_models_different_stages(self):
        """Test managing multiple models at different lifecycle stages."""
        # Create multiple models
        models_config = {
            "EquityTrend_v1": "live",
            "MeanReversion_v1": "paper",
            "Momentum_v1": "candidate",
            "NewStrategy_v1": "research"
        }

        # Set all lifecycle states
        with open(self.lifecycle_file, 'w') as f:
            json.dump(models_config, f)

        # Log progression for MeanReversion
        self._log_lifecycle_event("MeanReversion_v1", "candidate", "paper", "Promoted to paper", "user1")

        # Log progression for Momentum
        self._log_lifecycle_event("Momentum_v1", "research", "candidate", "Promoted to candidate", "user1")

        # Verify state file
        with open(self.lifecycle_file, 'r') as f:
            states = json.load(f)

        assert states["EquityTrend_v1"] == "live"
        assert states["MeanReversion_v1"] == "paper"
        assert states["Momentum_v1"] == "candidate"
        assert states["NewStrategy_v1"] == "research"

        # Verify event log
        with open(self.lifecycle_log, 'r') as f:
            events = [json.loads(line) for line in f]

        assert len(events) == 2

        # Find events by model name
        mean_rev_events = [e for e in events if e["model_name"] == "MeanReversion_v1"]
        momentum_events = [e for e in events if e["model_name"] == "Momentum_v1"]

        assert len(mean_rev_events) == 1
        assert len(momentum_events) == 1

    def test_lifecycle_audit_trail(self):
        """Test that complete lifecycle history is maintained."""
        model_name = "AuditTestModel"

        # Simulate complete lifecycle progression
        transitions = [
            ("research", "candidate", "Backtest Sharpe 1.5"),
            ("candidate", "paper", "Validation passed"),
            ("paper", "candidate", "Paper performance degraded"),
            ("candidate", "paper", "Re-validated after fixes"),
            ("paper", "live", "Paper trading successful"),
        ]

        current_stage = "research"
        for from_stage, to_stage, reason in transitions:
            assert current_stage == from_stage, f"Expected {from_stage}, got {current_stage}"
            self._update_lifecycle_state(model_name, to_stage)
            self._log_lifecycle_event(model_name, from_stage, to_stage, reason)
            current_stage = to_stage

        # Verify final state
        with open(self.lifecycle_file, 'r') as f:
            states = json.load(f)
        assert states[model_name] == "live"

        # Verify complete audit trail
        with open(self.lifecycle_log, 'r') as f:
            events = [json.loads(line) for line in f]

        assert len(events) == 5

        # Verify sequence
        assert events[0]["from_stage"] == "research"
        assert events[0]["to_stage"] == "candidate"

        assert events[1]["from_stage"] == "candidate"
        assert events[1]["to_stage"] == "paper"

        assert events[2]["from_stage"] == "paper"
        assert events[2]["to_stage"] == "candidate"  # Demotion

        assert events[3]["from_stage"] == "candidate"
        assert events[3]["to_stage"] == "paper"  # Re-promotion

        assert events[4]["from_stage"] == "paper"
        assert events[4]["to_stage"] == "live"

        # Verify all events for same model
        for event in events:
            assert event["model_name"] == model_name


# Run tests if executed directly
if __name__ == "__main__":
    print("=" * 80)
    print("Running Model Lifecycle Integration Tests")
    print("=" * 80)

    # Run with pytest
    pytest.main([__file__, "-v", "-s"])
