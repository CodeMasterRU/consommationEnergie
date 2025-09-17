"""Unit tests for numeric parsing helpers in Pydantic models.

The project depends on Pydantic models to clean numeric fields.  The
runtime dependencies (pydantic, pandas, etc.) are not installed in this
execution environment, so we provide a very small stub of the pieces of
Pydantic that the modules rely on.  The tests then import the modules and
validate the behaviour of the helper functions that normalise text inputs
into floats.
"""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture(autouse=True)
def stub_pydantic(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide a lightweight stub of :mod:`pydantic` for the tests.

    The project modules only use a handful of Pydantic utilities to
    declare models.  Re-creating the full dependency tree would be very
    heavyweight for unit tests, so we supply a minimal implementation
    that supports the required call signatures.  The helper functions we
    test do not depend on any of the advanced Pydantic features.
    """

    project_root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(project_root))

    if "pydantic" in sys.modules:
        # Another test (or an earlier import) already provided the stub.
        return

    stub = types.ModuleType("pydantic")

    class _BaseModel:
        """Simplified stand-in for :class:`pydantic.BaseModel`."""

        def __init__(self, **data: Any) -> None:  # pragma: no cover - not used
            for key, value in data.items():
                setattr(self, key, value)

    def _field(default: Any = None, *args: Any, **kwargs: Any) -> Any:
        """Return the declared default value (ignoring metadata)."""

        return default

    def _config_dict(**kwargs: Any) -> dict[str, Any]:
        return dict(**kwargs)

    def _field_validator(*validator_args: Any, **validator_kwargs: Any):
        def decorator(func):
            return func

        return decorator

    stub.BaseModel = _BaseModel
    stub.Field = _field
    stub.ConfigDict = _config_dict
    stub.field_validator = _field_validator

    monkeypatch.setitem(sys.modules, "pydantic", stub)


def import_module(name: str):
    """Import *name*, reloading the module if it was already loaded."""

    if name in sys.modules:
        return importlib.reload(sys.modules[name])
    return importlib.import_module(name)


def test_eco2mix_to_float_parses_numeric_strings(monkeypatch: pytest.MonkeyPatch) -> None:
    module = import_module("api.models.eco2mix_national")

    to_float = module._to_float

    assert to_float(None) is None
    assert to_float(42) == 42.0
    assert to_float(3.14) == pytest.approx(3.14)
    # Spaces, thousands separators and units are removed.
    assert to_float(" 1\u202f234,56 MW ") == pytest.approx(1234.56)
    # Negative values and dots are preserved.
    assert to_float("-987.5") == pytest.approx(-987.5)
    # Mixed alphanumeric strings keep only the numeric part.
    assert to_float("2 500kWh") == pytest.approx(2500.0)


def test_eco2mix_to_float_handles_special_markers(monkeypatch: pytest.MonkeyPatch) -> None:
    module = import_module("api.models.eco2mix_national")
    to_float = module._to_float

    # 'ND' (no data) is explicitly normalised to None.
    assert to_float("ND") is None
    assert to_float(" nd ") is None
    # Completely non-numeric values fall back to None as well.
    assert to_float("aucune donnée") is None


def test_major_installations_to_float_differs_on_invalid_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = import_module("api.models.major_installations")
    to_float = module._to_float

    assert to_float(None) is None
    assert to_float("1 000,5") == pytest.approx(1000.5)
    assert to_float("-12,0") == pytest.approx(-12.0)
    # Unlike the eco2mix helper, invalid strings are returned unchanged.
    invalid = "hors champ"
    assert to_float(invalid) == invalid
    # Partial numeric information is still extracted.
    assert to_float("Valeur : 75,25") == pytest.approx(75.25)


