"""Scaffold tests verifying environment and basic setup."""

import pytest
from experiments.run_experiment import parse_args


def test_package_scaffold():
    """Verify that base packages are importable."""
    import sim
    import brain
    import experiments

    assert sim.__version__ == "0.1.0"
    assert brain.__version__ == "0.1.0"
    assert experiments.__version__ == "0.1.0"


def test_cli_argument_parsing():
    """Verify CLI argument defaults and custom flags."""
    args = parse_args(["--seed", "123", "--ticks", "1000", "--agent", "random"])
    assert args.seed == 123
    assert args.ticks == 1000
    assert args.agent == "random"
