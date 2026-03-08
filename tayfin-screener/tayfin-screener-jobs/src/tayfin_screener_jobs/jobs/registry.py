"""Job registry for tayfin-screener-jobs.

Maps job names (from config/CLI) to their concrete Job classes.
New jobs are registered by adding an entry to ``_REGISTRY``.
"""

from __future__ import annotations

import importlib

# Lazy imports to avoid circular dependencies; resolved at look-up time.
# Format: "job_name" → "module_name.ClassName"
_REGISTRY: dict[str, str] = {
    "vcp_screen": "vcp_screen_job.VcpScreenJob",
    "mcsa_screen": "mcsa_screen_job.McsaScreenJob",
}


def get_job_class(job_name: str):
    """Return the Job class registered under *job_name*.

    Raises ``KeyError`` if *job_name* is not in the registry.
    """
    entry = _REGISTRY.get(job_name)
    if entry is None:
        raise KeyError(f"Unknown job: {job_name!r}. Available: {list(_REGISTRY)}")
    module_name, class_name = entry.rsplit(".", 1)
    mod = importlib.import_module(f".{module_name}", package=__package__)
    return getattr(mod, class_name)
