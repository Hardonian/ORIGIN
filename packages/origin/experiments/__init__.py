"""ORIGIN experiments package."""

from origin.experiments.runner import ALGORITHMS, run_experiment, run_trial, validate_config
from origin.experiments.store import Store


def api_main(argv: list[str] | None = None) -> int:
    """Launch the API lazily without pre-importing its ``python -m`` target."""
    from origin.experiments.api import main

    return main(argv)


__all__ = ["ALGORITHMS", "Store", "run_experiment", "run_trial", "validate_config", "api_main"]
