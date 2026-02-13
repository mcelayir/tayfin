"""Job registry for tayfin-indicator-jobs.

Maps job names (from config/CLI) to their concrete Job classes.
New jobs are registered by adding an entry to ``REGISTRY``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .ma_compute_job import MaComputeJob  # noqa: F401

# Lazy imports to avoid circular dependencies; resolved at look-up time.
_REGISTRY: dict[str, str] = {
    "ma_compute": "ma_compute_job.MaComputeJob",
    "atr_compute": "atr_compute_job.AtrComputeJob",
    "vol_sma_compute": "vol_sma_compute_job.VolSmaComputeJob",
    "rolling_high_compute": "rolling_high_compute_job.RollingHighComputeJob",
}


def get_job_class(job_name: str):
    """Return the Job class registered under *job_name*."""
    entry = _REGISTRY.get(job_name)
    if entry is None:
        raise KeyError(f"Unknown job: {job_name!r}. Available: {list(_REGISTRY)}")
    module_name, class_name = entry.rsplit(".", 1)
    import importlib

    mod = importlib.import_module(f".{module_name}", package=__package__)
    return getattr(mod, class_name)
