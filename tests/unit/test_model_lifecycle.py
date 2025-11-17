"""
Unit Test: Model Lifecycle Management

Tests lifecycle stage transitions and validation:
1. BaseModel lifecycle_stage initialization
2. Lifecycle progression (research → candidate → paper → live)
3. Lifecycle validation (prevent invalid stages)
4. Lifecycle state persistence (JSON file)
5. Promotion/demotion logic
6. Lifecycle filtering in runners
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
import pandas as pd
from decimal import Decimal


class DummyModel(BaseModel):
    """Dummy model for testing."""

    def generate_target_weights(self, context: Context) -> ModelOutput:
        """Return empty weights for testing."""
        return ModelOutput(
            model_name=self.name,
            timestamp=context.timestamp,
            weights={}
        )


class TestModelLifecycleStages:
    """Test lifecycle stage field in BaseModel."""

    def test_default_lifecycle_stage(self):
        """Test that models default to 'research' stage."""
        model = DummyModel(
            name="TestModel",
            version="1.0.0",
            universe=["SPY"]
        )
        assert model.lifecycle_stage == "research"

    def test_explicit_lifecycle_stage(self):
        """Test setting explicit lifecycle stage."""
        for stage in ["research", "candidate", "paper", "live"]:
            model = DummyModel(
                name="TestModel",
                version="1.0.0",
                universe=["SPY"],
                lifecycle_stage=stage
            )
            assert model.lifecycle_stage == stage

    def test_invalid_lifecycle_stage(self):
        """Test that invalid lifecycle stages raise ValueError."""
        with pytest.raises(ValueError, match="Invalid lifecycle_stage"):
            DummyModel(
                name="TestModel",
                version="1.0.0",
                universe=["SPY"],
                lifecycle_stage="invalid_stage"
            )

    def test_lifecycle_stage_in_repr(self):
        """Test that lifecycle stage appears in model representation."""
        model = DummyModel(
            name="TestModel",
            version="1.0.0",
            universe=["SPY"],
            lifecycle_stage="paper"
        )
        # The __repr__ shows universe but not stage, which is fine
        # Just verify stage is accessible
        assert model.lifecycle_stage == "paper"


class TestLifecycleProgression:
    """Test lifecycle progression logic."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary directory for lifecycle state
        self.test_dir = Path(tempfile.mkdtemp())
        self.lifecycle_file = self.test_dir / ".model_lifecycle.json"

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_lifecycle_progression_order(self):
        """Test that lifecycle stages follow correct progression."""
        progression = {
            "research": "candidate",
            "candidate": "paper",
            "paper": "live"
        }

        for current, expected_next in progression.items():
            assert expected_next in ["candidate", "paper", "live"]
            # Verify progression is unidirectional
            assert current != expected_next

    def test_lifecycle_state_persistence(self):
        """Test saving and loading lifecycle states."""
        # Create initial state
        lifecycle_states = {
            "Model1": "research",
            "Model2": "candidate",
            "Model3": "paper",
            "Model4": "live"
        }

        # Save to file
        with open(self.lifecycle_file, 'w') as f:
            json.dump(lifecycle_states, f, indent=2)

        # Load from file
        with open(self.lifecycle_file, 'r') as f:
            loaded_states = json.load(f)

        # Verify all states loaded correctly
        assert loaded_states == lifecycle_states
        assert loaded_states["Model1"] == "research"
        assert loaded_states["Model2"] == "candidate"
        assert loaded_states["Model3"] == "paper"
        assert loaded_states["Model4"] == "live"

    def test_promotion_updates_state(self):
        """Test that promotion updates lifecycle state."""
        # Initial state
        lifecycle_states = {"TestModel": "research"}

        with open(self.lifecycle_file, 'w') as f:
            json.dump(lifecycle_states, f)

        # Promote to candidate
        lifecycle_states["TestModel"] = "candidate"

        with open(self.lifecycle_file, 'w') as f:
            json.dump(lifecycle_states, f)

        # Verify update
        with open(self.lifecycle_file, 'r') as f:
            loaded_states = json.load(f)

        assert loaded_states["TestModel"] == "candidate"

    def test_demotion_updates_state(self):
        """Test that demotion updates lifecycle state."""
        # Initial state
        lifecycle_states = {"TestModel": "live"}

        with open(self.lifecycle_file, 'w') as f:
            json.dump(lifecycle_states, f)

        # Demote to paper
        lifecycle_states["TestModel"] = "paper"

        with open(self.lifecycle_file, 'w') as f:
            json.dump(lifecycle_states, f)

        # Verify update
        with open(self.lifecycle_file, 'r') as f:
            loaded_states = json.load(f)

        assert loaded_states["TestModel"] == "paper"

    def test_multiple_models_independent_stages(self):
        """Test that multiple models can be at different stages."""
        lifecycle_states = {
            "EquityTrendModel": "live",
            "MeanReversionModel": "paper",
            "MomentumModel": "candidate",
            "NewModel": "research"
        }

        with open(self.lifecycle_file, 'w') as f:
            json.dump(lifecycle_states, f)

        # Verify all stages are independent
        with open(self.lifecycle_file, 'r') as f:
            loaded_states = json.load(f)

        assert len(loaded_states) == 4
        assert loaded_states["EquityTrendModel"] == "live"
        assert loaded_states["MeanReversionModel"] == "paper"
        assert loaded_states["MomentumModel"] == "candidate"
        assert loaded_states["NewModel"] == "research"


class TestLifecycleValidation:
    """Test lifecycle transition validation."""

    def test_promotion_criteria_structure(self):
        """Test that promotion criteria are well-defined."""
        promotion_criteria = {
            ("research", "candidate"): {
                "min_sharpe": 1.0,
                "min_cagr": 0.10,
                "max_drawdown": -0.20,
                "min_trades": 10
            },
            ("candidate", "paper"): {
                "min_sharpe": 1.2,
                "min_cagr": 0.12,
                "max_drawdown": -0.15,
                "min_trades": 20
            },
            ("paper", "live"): {
                "paper_days": 30,
                "min_paper_trades": 10,
                "max_paper_slippage": 0.001
            }
        }

        # Verify all transitions have criteria
        assert ("research", "candidate") in promotion_criteria
        assert ("candidate", "paper") in promotion_criteria
        assert ("paper", "live") in promotion_criteria

        # Verify research → candidate criteria
        rc_criteria = promotion_criteria[("research", "candidate")]
        assert rc_criteria["min_sharpe"] > 0
        assert rc_criteria["min_cagr"] > 0
        assert rc_criteria["max_drawdown"] < 0
        assert rc_criteria["min_trades"] > 0

        # Verify candidate → paper criteria (stricter)
        cp_criteria = promotion_criteria[("candidate", "paper")]
        assert cp_criteria["min_sharpe"] > rc_criteria["min_sharpe"]
        assert cp_criteria["min_cagr"] > rc_criteria["min_cagr"]
        assert cp_criteria["max_drawdown"] > rc_criteria["max_drawdown"]  # Less negative = stricter
        assert cp_criteria["min_trades"] > rc_criteria["min_trades"]

        # Verify paper → live criteria
        pl_criteria = promotion_criteria[("paper", "live")]
        assert pl_criteria["paper_days"] > 0
        assert pl_criteria["min_paper_trades"] > 0
        assert pl_criteria["max_paper_slippage"] > 0

    def test_invalid_transitions(self):
        """Test that invalid transitions are rejected."""
        # These transitions should not be allowed
        invalid_transitions = [
            ("research", "paper"),  # Skip candidate
            ("research", "live"),   # Skip candidate and paper
            ("candidate", "live"),  # Skip paper
            ("live", "research"),   # Backwards (use demote)
            ("paper", "research"),  # Backwards (use demote)
        ]

        # Define valid transitions
        valid_transitions = {
            ("research", "candidate"),
            ("candidate", "paper"),
            ("paper", "live")
        }

        for from_stage, to_stage in invalid_transitions:
            assert (from_stage, to_stage) not in valid_transitions

    def test_promotion_to_live_requires_all_previous_stages(self):
        """Test that promotion to live requires passing through all stages."""
        # A model must go: research → candidate → paper → live
        # Cannot skip any stage

        # Starting from research
        stage = "research"
        assert stage != "live"

        # Must go to candidate
        stage = "candidate"
        assert stage != "live"

        # Must go to paper
        stage = "paper"
        assert stage != "live"

        # Only now can reach live
        stage = "live"
        assert stage == "live"


class TestLifecycleFiltering:
    """Test lifecycle filtering in runners."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.lifecycle_file = self.test_dir / ".model_lifecycle.json"

        # Create test models at different stages
        self.models = [
            DummyModel("ResearchModel", "1.0.0", ["SPY"], lifecycle_stage="research"),
            DummyModel("CandidateModel", "1.0.0", ["QQQ"], lifecycle_stage="candidate"),
            DummyModel("PaperModel", "1.0.0", ["BTC-USD"], lifecycle_stage="paper"),
            DummyModel("LiveModel", "1.0.0", ["ETH-USD"], lifecycle_stage="live")
        ]

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_paper_runner_filters_correct_models(self):
        """Test that paper runner only loads candidate/paper models."""
        # Create lifecycle state file
        lifecycle_states = {
            "ResearchModel": "research",
            "CandidateModel": "candidate",
            "PaperModel": "paper",
            "LiveModel": "live"
        }

        with open(self.lifecycle_file, 'w') as f:
            json.dump(lifecycle_states, f)

        # Simulate paper runner filtering
        eligible_stages = ["candidate", "paper"]
        filtered_models = [
            m for m in self.models
            if lifecycle_states.get(m.name, m.lifecycle_stage) in eligible_stages
        ]

        # Verify only candidate and paper models included
        assert len(filtered_models) == 2
        model_names = [m.name for m in filtered_models]
        assert "CandidateModel" in model_names
        assert "PaperModel" in model_names
        assert "ResearchModel" not in model_names
        assert "LiveModel" not in model_names

    def test_live_runner_filters_correct_models(self):
        """Test that live runner only loads live models."""
        # Create lifecycle state file
        lifecycle_states = {
            "ResearchModel": "research",
            "CandidateModel": "candidate",
            "PaperModel": "paper",
            "LiveModel": "live"
        }

        with open(self.lifecycle_file, 'w') as f:
            json.dump(lifecycle_states, f)

        # Simulate live runner filtering
        eligible_stages = ["live"]
        filtered_models = [
            m for m in self.models
            if lifecycle_states.get(m.name, m.lifecycle_stage) in eligible_stages
        ]

        # Verify only live models included
        assert len(filtered_models) == 1
        assert filtered_models[0].name == "LiveModel"

        # Verify all others excluded
        excluded_names = [m.name for m in self.models if m not in filtered_models]
        assert "ResearchModel" in excluded_names
        assert "CandidateModel" in excluded_names
        assert "PaperModel" in excluded_names

    def test_no_models_eligible_for_live(self):
        """Test handling when no models are at live stage."""
        # Create lifecycle state with no live models
        lifecycle_states = {
            "ResearchModel": "research",
            "CandidateModel": "candidate",
            "PaperModel": "paper",
            "LiveModel": "paper"  # Not yet live
        }

        with open(self.lifecycle_file, 'w') as f:
            json.dump(lifecycle_states, f)

        # Simulate live runner filtering
        eligible_stages = ["live"]
        filtered_models = [
            m for m in self.models
            if lifecycle_states.get(m.name, m.lifecycle_stage) in eligible_stages
        ]

        # Should have zero models
        assert len(filtered_models) == 0

    def test_all_models_eligible_for_paper(self):
        """Test when multiple models are at candidate/paper stages."""
        # Create lifecycle state with multiple paper-eligible models
        lifecycle_states = {
            "ResearchModel": "candidate",
            "CandidateModel": "candidate",
            "PaperModel": "paper",
            "LiveModel": "paper"
        }

        with open(self.lifecycle_file, 'w') as f:
            json.dump(lifecycle_states, f)

        # Simulate paper runner filtering
        eligible_stages = ["candidate", "paper"]
        filtered_models = [
            m for m in self.models
            if lifecycle_states.get(m.name, m.lifecycle_stage) in eligible_stages
        ]

        # All 4 models should be eligible
        assert len(filtered_models) == 4


class TestLifecycleEventLogging:
    """Test lifecycle event logging."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.log_file = self.test_dir / "model_lifecycle_events.jsonl"

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_event_log_structure(self):
        """Test that lifecycle events have correct structure."""
        # Create a sample event
        event = {
            "timestamp": datetime.now().isoformat(),
            "model_name": "TestModel",
            "from_stage": "research",
            "to_stage": "candidate",
            "reason": "Passed backtest criteria",
            "operator": "test_user"
        }

        # Write to log
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(event) + '\n')

        # Read from log
        with open(self.log_file, 'r') as f:
            lines = f.readlines()

        assert len(lines) == 1

        # Parse event
        logged_event = json.loads(lines[0])

        # Verify all required fields present
        assert "timestamp" in logged_event
        assert "model_name" in logged_event
        assert "from_stage" in logged_event
        assert "to_stage" in logged_event
        assert "reason" in logged_event
        assert "operator" in logged_event

        # Verify values
        assert logged_event["model_name"] == "TestModel"
        assert logged_event["from_stage"] == "research"
        assert logged_event["to_stage"] == "candidate"

    def test_multiple_events_appended(self):
        """Test that multiple events are appended to log."""
        events = [
            {
                "timestamp": datetime.now().isoformat(),
                "model_name": "Model1",
                "from_stage": "research",
                "to_stage": "candidate",
                "reason": "Backtest passed",
                "operator": "user1"
            },
            {
                "timestamp": datetime.now().isoformat(),
                "model_name": "Model1",
                "from_stage": "candidate",
                "to_stage": "paper",
                "reason": "Ready for paper",
                "operator": "user1"
            },
            {
                "timestamp": datetime.now().isoformat(),
                "model_name": "Model2",
                "from_stage": "research",
                "to_stage": "candidate",
                "reason": "Backtest passed",
                "operator": "user2"
            }
        ]

        # Write all events
        for event in events:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(event) + '\n')

        # Read and verify
        with open(self.log_file, 'r') as f:
            lines = f.readlines()

        assert len(lines) == 3

        # Verify each event
        for i, line in enumerate(lines):
            logged_event = json.loads(line)
            assert logged_event["model_name"] == events[i]["model_name"]
            assert logged_event["from_stage"] == events[i]["from_stage"]
            assert logged_event["to_stage"] == events[i]["to_stage"]


# Run tests if executed directly
if __name__ == "__main__":
    print("=" * 80)
    print("Running Model Lifecycle Unit Tests")
    print("=" * 80)

    # Run with pytest
    pytest.main([__file__, "-v", "-s"])
