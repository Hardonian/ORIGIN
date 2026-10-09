"""ORIGIN experiments package."""

from importlib import import_module
from typing import Any

from origin.experiments.store import Store

_RUNNER_EXPORTS = frozenset({"ALGORITHMS", "run_experiment", "run_trial", "validate_config"})


def __getattr__(name: str) -> Any:
    """Expose runner helpers without pre-importing a ``python -m`` target.

    Importing ``runner`` here makes ``python -m origin.experiments.runner``
    execute a module that is already in ``sys.modules``, which produces a
    misleading runtime warning.  Keep the historical package-level API, but
    import the runner only when one of its exports is actually requested.
    """
    if name in _RUNNER_EXPORTS:
        runner = import_module(".runner", __name__)
        return getattr(runner, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def api_main(argv: list[str] | None = None) -> int:
    """Launch the API lazily without pre-importing its ``python -m`` target."""
    from origin.experiments.api import main

    return main(argv)


__all__ = ["ALGORITHMS", "Store", "run_experiment", "run_trial", "validate_config", "api_main"]
