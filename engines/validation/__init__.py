"""
Validation Tools for Trading Strategy Testing

Provides tools to validate that strategies have genuine edge:
- Monkey tests: Compare strategy vs random baselines
- Component tests: Isolate which parts of strategy work
- Data burn tracking: Prevent re-using test data

Usage:
    # Monkey test - validate strategy beats random chance
    from engines.validation.monkey_tests import monkey_test
    result = monkey_test(model, config, n_variants=1000)
    assert result.passes()  # Must beat >90% of random variants

    # Component test - identify source of edge
    from engines.validation.component_tests import component_test
    result = component_test(model, config)
    print(f"Primary edge: {'entry' if result.entry_pct > 50 else 'exit'}")

    # Data burn tracking - prevent contamination
    from engines.validation.data_burn import get_tracker
    tracker = get_tracker()
    is_clean = tracker.check_and_warn(model_name, start_date, end_date, ...)

CLI Tools:
    python -m engines.validation.monkey_test_cli --profile exp_standalone_v3 --variants 1000
    python -m engines.validation.component_test_cli --profile exp_standalone_v3 --samples 10
    python -m engines.validation.data_burn_cli log --model SectorRotationModel_v1
"""

from engines.validation.monkey_tests import (
    monkey_test,
    MonkeyTester,
    MonkeyTestResult,
    RandomModelWrapper
)

from engines.validation.component_tests import (
    component_test,
    ComponentTester,
    ComponentTestResult
)

from engines.validation.data_burn import (
    DataBurnTracker,
    BurnRecord,
    get_tracker
)

__all__ = [
    # Monkey tests
    'monkey_test',
    'MonkeyTester',
    'MonkeyTestResult',
    'RandomModelWrapper',

    # Component tests
    'component_test',
    'ComponentTester',
    'ComponentTestResult',

    # Data burn tracking
    'DataBurnTracker',
    'BurnRecord',
    'get_tracker',
]
