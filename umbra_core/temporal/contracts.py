"""D-010 ElapsedTimeContract registry and pure effect calculation (§4.4)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from umbra_core.temporal.state import AnchorTrustClass, canonical_serialize
from umbra_core.util import canon_json, new_id, sha256_hex

ELAPSED_CONTRACT_REGISTRY_SCHEMA = "d010.elapsed-contract-registry.v1"
ELAPSED_EFFECT_SCHEMA = "d010.elapsed-effect.v1"

REQUIRED_ELAPSED_CONTRACT_UNAVAILABLE = "REQUIRED_ELAPSED_CONTRACT_UNAVAILABLE"
ELAPSED_CONTRACT_REGISTRY_MISMATCH = "ELAPSED_CONTRACT_REGISTRY_MISMATCH"
ELAPSED_CONTRACT_PLAN_INVALID = "ELAPSED_CONTRACT_PLAN_INVALID"


class ElapsedContractError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ElapsedEffectPlan:
    effect_plan_id: str
    contract_id: str
    contract_version: int
    contract_hash: str
    expected_subsystem_state_version: int
    expected_subsystem_state_hash: str
    declarative_effects: tuple[dict[str, Any], ...]
    effect_plan_hash: str


@dataclass(frozen=True)
class ElapsedTimeContract:
    contract_id: str
    contract_version: int
    contract_hash: str
    subsystem: str
    maximum_elapsed: float
    maximum_uncertainty: float
    supported_trust_classes: frozenset[str]
    required_for_trust_classes: frozenset[str]
    effect_schema_id: str
    supported_effects: frozenset[str]


@dataclass(frozen=True)
class ElapsedTimeContractRegistry:
    schema_version: str
    registry_version: int
    registry_hash: str
    contracts: tuple[ElapsedTimeContract, ...]


def _contract_hash(contract: dict[str, Any]) -> str:
    payload = dict(contract)
    payload.pop("contract_hash", None)
    return sha256_hex(canon_json(canonical_serialize(payload)))


def _registry_hash(contracts: tuple[ElapsedTimeContract, ...], schema_version: str, registry_version: int) -> str:
    payload = {
        "schema_version": schema_version,
        "registry_version": registry_version,
        "contracts": [
            {
                "contract_id": c.contract_id,
                "contract_version": c.contract_version,
                "contract_hash": c.contract_hash,
            }
            for c in contracts
        ],
    }
    return sha256_hex(canon_json(payload))


def load_elapsed_contract_registry(path: str | Path | None = None) -> ElapsedTimeContractRegistry:
    if path is None:
        path = Path(__file__).resolve().parents[2] / "experiments/d010/elapsed-contract-registry.json"
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    schema_version = str(raw["schema_version"])
    registry_version = int(raw["registry_version"])
    contracts: list[ElapsedTimeContract] = []
    for item in raw.get("contracts") or []:
        contract_hash = str(item.get("contract_hash") or _contract_hash(item))
        contracts.append(
            ElapsedTimeContract(
                contract_id=str(item["contract_id"]),
                contract_version=int(item["contract_version"]),
                contract_hash=contract_hash,
                subsystem=str(item["subsystem"]),
                maximum_elapsed=float(item["maximum_elapsed"]),
                maximum_uncertainty=float(item["maximum_uncertainty"]),
                supported_trust_classes=frozenset(str(x) for x in item["supported_trust_classes"]),
                required_for_trust_classes=frozenset(str(x) for x in item.get("required_for_trust_classes") or []),
                effect_schema_id=str(item["effect_schema_id"]),
                supported_effects=frozenset(str(x) for x in item["supported_effects"]),
            )
        )
    registry_hash = _registry_hash(tuple(contracts), schema_version, registry_version)
    declared = raw.get("registry_hash")
    if declared and str(declared) != registry_hash:
        raise ElapsedContractError(ELAPSED_CONTRACT_REGISTRY_MISMATCH)
    return ElapsedTimeContractRegistry(
        schema_version=schema_version,
        registry_version=registry_version,
        registry_hash=registry_hash,
        contracts=tuple(contracts),
    )


def _effect_plan_hash(plan_payload: dict[str, Any]) -> str:
    return sha256_hex(canon_json(canonical_serialize(plan_payload)))


def calculate_effects(
    contract: ElapsedTimeContract,
    *,
    snapshot: dict[str, Any],
    elapsed_seconds: float,
    uncertainty: float,
    trust_class: AnchorTrustClass,
) -> ElapsedEffectPlan | None:
    if trust_class.value not in contract.supported_trust_classes:
        return None
    if elapsed_seconds > contract.maximum_elapsed:
        return None
    if uncertainty > contract.maximum_uncertainty:
        return None

    state_version = int(snapshot.get("state_version", 0))
    state_hash = str(snapshot.get("state_hash", ""))
    effects: list[dict[str, Any]] = []
    for effect_name in sorted(contract.supported_effects):
        effects.append(
            {
                "effect": effect_name,
                "subsystem": contract.subsystem,
                "elapsed_seconds": elapsed_seconds,
                "trust_class": trust_class.value,
            }
        )
    plan_payload = {
        "contract_id": contract.contract_id,
        "contract_version": contract.contract_version,
        "contract_hash": contract.contract_hash,
        "expected_subsystem_state_version": state_version,
        "expected_subsystem_state_hash": state_hash,
        "declarative_effects": effects,
    }
    effect_plan_hash = _effect_plan_hash(plan_payload)
    return ElapsedEffectPlan(
        effect_plan_id=f"effect:{new_id()}",
        contract_id=contract.contract_id,
        contract_version=contract.contract_version,
        contract_hash=contract.contract_hash,
        expected_subsystem_state_version=state_version,
        expected_subsystem_state_hash=state_hash,
        declarative_effects=tuple(effects),
        effect_plan_hash=effect_plan_hash,
    )


def calculate_all_effects(
    registry: ElapsedTimeContractRegistry,
    *,
    subsystem_snapshots: dict[str, dict[str, Any]],
    elapsed_seconds: float,
    uncertainty: float,
    trust_class: AnchorTrustClass,
) -> tuple[list[ElapsedEffectPlan], list[str], bool]:
    """Return (plans, skipped_optional_ids, required_failure)."""
    plans: list[ElapsedEffectPlan] = []
    skipped: list[str] = []
    required_failure = False

    for contract in registry.contracts:
        snapshot = subsystem_snapshots.get(contract.subsystem)
        if snapshot is None:
            if trust_class.value in contract.required_for_trust_classes:
                required_failure = True
            else:
                skipped.append(contract.contract_id)
            continue
        plan = calculate_effects(
            contract,
            snapshot=snapshot,
            elapsed_seconds=elapsed_seconds,
            uncertainty=uncertainty,
            trust_class=trust_class,
        )
        if plan is None:
            if trust_class.value in contract.required_for_trust_classes:
                required_failure = True
            else:
                skipped.append(contract.contract_id)
            continue
        plans.append(plan)
    return plans, skipped, required_failure
