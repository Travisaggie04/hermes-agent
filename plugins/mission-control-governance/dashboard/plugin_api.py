"""Dashboard loader wrapper for the Mission Control governance API."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


_api_path = Path(__file__).resolve().parents[1] / "api.py"
_spec = importlib.util.spec_from_file_location(
    "hermes_mission_control_governance_api",
    _api_path,
)
if _spec is None or _spec.loader is None:
    raise RuntimeError("Unable to load Mission Control governance API")
_module = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _module
_spec.loader.exec_module(_module)

router = _module.router
