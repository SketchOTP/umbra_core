"""AS-016 downstream qualification under the repaired configuration."""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Any, Iterator

from experiments.as015 import downstream as _as015
from experiments.as016.full_config import BASELINE, DIRECTIVE, config, fingerprint


ACCELERATED = dict(_as015.ACCELERATED)
SOAK = dict(_as015.SOAK)
VARIANTS = _as015.VARIANTS


@contextlib.contextmanager
def _as016_config_scope() -> Iterator[None]:
    original = (_as015.config, _as015.fingerprint, _as015.DIRECTIVE, _as015.BASELINE)
    _as015.config, _as015.fingerprint = config, fingerprint
    _as015.DIRECTIVE, _as015.BASELINE = DIRECTIVE, BASELINE
    try:
        yield
    finally:
        _as015.config, _as015.fingerprint, _as015.DIRECTIVE, _as015.BASELINE = original


def _decorate(result: dict[str, Any], schema: str) -> dict[str, Any]:
    value = dict(result)
    value.update(
        schema=schema,
        directive=DIRECTIVE,
        baseline=BASELINE,
        canonical_configuration="AS016_FULL_CONFIGURATION",
    )
    return value


def boundedness(seed: int, work: Path, ticks: int = ACCELERATED["ticks"], *, ledger_overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    with _as016_config_scope():
        return _decorate(
            _as015.boundedness(seed, work, ticks, ledger_overrides=ledger_overrides),
            "AS016_BOUNDEDNESS_RESULT_V1",
        )


def soak(seed: int, work: Path, *, warmup_seconds: float = SOAK["warmup_seconds"], measure_seconds: float = SOAK["measure_seconds"], ledger_overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    with _as016_config_scope():
        return _decorate(
            _as015.soak(
                seed, work, warmup_seconds=warmup_seconds,
                measure_seconds=measure_seconds, ledger_overrides=ledger_overrides,
            ),
            "AS016_REALTIME_SOAK_RESULT_V1",
        )


def lifecycle(seed: int, work: Path, *, ledger_overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    with _as016_config_scope():
        return _decorate(
            _as015.lifecycle(seed, work, ledger_overrides=ledger_overrides),
            "AS016_LIFECYCLE_RESULT_V1",
        )


def ablation(seed: int, work: Path, variant: str, ticks: int = 7200, *, ledger_overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    with _as016_config_scope():
        return _decorate(
            _as015.ablation(seed, work, variant, ticks, ledger_overrides=ledger_overrides),
            "AS016_ABLATION_RESULT_V1",
        )


__all__ = ["ACCELERATED", "SOAK", "VARIANTS", "ablation", "boundedness", "lifecycle", "soak"]
