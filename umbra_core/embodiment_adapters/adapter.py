"""EmbodimentAdapter — thin governed body-profile constraint enforcement.

Attach/detach/swap append authoritative attachment events. `execute()` validates
a request against the current attachment + body-profile constraints; on success
it delegates the sole world mutation to `Embodiment.execute_primitive`; on
rejection it returns a failed raw result (`ok_raw=False`) without ever touching
`Embodiment` — governance verifies and commits that failed outcome through the
existing `outcome_verified` path exactly like any other executed capability.

Supplement S1 (design doc, 2026-07-23): supported continuous parameters
(currently `step` for MOVE/APPROACH/RETREAT) that exceed a profile's physical
limit are clamped to that limit rather than hard-rejected — clamping is not a
failure. `BODY_LIMIT_REJECTED` stays reserved for malformed/non-finite/
non-positive requests or limits a profile marks non-clampable via a
`"<limit>_clampable": False` entry in `physical_limits` (absent means
clampable). The original `AdapterRequest.params` is never mutated; a
translated copy is built with provenance back to the request.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any, Callable

from umbra_core.embodiment import Embodiment
from umbra_core.embodiment_adapters.profiles import BodyProfile, get_profile, profile_definition_hash
from umbra_core.persistence import Store
from umbra_core.util import SeededRNG, new_id

ATTACHMENT_EVENT_TYPES = (
    "embodiment_body_attached",
    "embodiment_body_detached",
    "embodiment_body_profile_swapped",
)

ADAPTER_FAILURE_CODES = frozenset(
    {
        "UNSUPPORTED_BODY_CAPABILITY",
        "BODY_LIMIT_REJECTED",
        "BODY_DETACHED",
        "STALE_ATTACHMENT_GENERATION",
        "PROFILE_HASH_MISMATCH",
    }
)


class AdapterError(Exception):
    """Fail-closed attach/detach/swap error."""


@dataclass
class AdapterRequest:
    """Body-neutral execution request issued by governance to the adapter."""

    request_id: str
    capability: str
    params: dict[str, Any]
    attachment_generation: int
    tick: int = 0
    expected_profile_hash: str | None = None


@dataclass
class AttachmentState:
    """Authoritative attachment record — persisted via embodiment_body_* events."""

    body_instance_id: str | None = None
    body_profile_id: str | None = None
    attachment_status: str = "DETACHED"  # DETACHED | ATTACHED
    attachment_generation: int = 0

    def to_state(self) -> dict[str, Any]:
        return {
            "body_instance_id": self.body_instance_id,
            "body_profile_id": self.body_profile_id,
            "attachment_status": self.attachment_status,
            "attachment_generation": self.attachment_generation,
        }

    @classmethod
    def from_state(cls, d: dict[str, Any]) -> AttachmentState:
        return cls(
            body_instance_id=d.get("body_instance_id"),
            body_profile_id=d.get("body_profile_id"),
            attachment_status=str(d.get("attachment_status", "DETACHED")),
            attachment_generation=int(d.get("attachment_generation", 0)),
        )


def attachment_state_from_event(event: dict[str, Any] | None) -> AttachmentState:
    """Reconstruct authoritative `AttachmentState` from the latest ledger
    attach/detach/swap event — the ledger, not the snapshot, is the source of
    truth for attachment (a snapshot may lag behind a crash-before-snapshot
    attach/detach/swap). `None` (no attachment event ever recorded) means a
    pre-D-008 organism awaiting migration."""
    if event is None:
        return AttachmentState()
    event_type = event["event_type"]
    payload = event["payload"]
    if event_type == "embodiment_body_attached":
        return AttachmentState(
            body_instance_id=payload["new_body_instance_id"],
            body_profile_id=payload["new_profile_id"],
            attachment_status="ATTACHED",
            attachment_generation=int(payload["new_generation"]),
        )
    if event_type == "embodiment_body_profile_swapped":
        return AttachmentState(
            body_instance_id=payload["body_instance_id"],
            body_profile_id=payload["new_profile_id"],
            attachment_status="ATTACHED",
            attachment_generation=int(payload["new_generation"]),
        )
    if event_type == "embodiment_body_detached":
        return AttachmentState(
            body_instance_id=payload["body_instance_id"],
            body_profile_id=None,
            attachment_status="DETACHED",
            attachment_generation=int(payload["new_generation"]),
        )
    raise ValueError(f"not_an_attachment_event:{event_type}")


class EmbodimentAdapter:
    """Enforces body-profile capability/limit constraints; never grants authority.

    All authoritative world mutation stays inside `Embodiment.execute_primitive`.
    The adapter can only narrow what governance already admitted — it can never
    widen it (see `test_adapter_cannot_grant_capabilities`).
    """

    _CONTINUOUS_STEP_CAPABILITIES = ("MOVE", "APPROACH", "RETREAT")

    def __init__(
        self,
        *,
        store: Store,
        agent_id: str,
        state: AttachmentState | None = None,
        profile_resolver: Callable[[str], BodyProfile] = get_profile,
        wall_time_fn: Callable[[], float] = time.time,
        monotonic_time_fn: Callable[[], float] | None = None,
    ):
        self.store = store
        self.agent_id = agent_id
        self.state = state or AttachmentState()
        self._resolve_profile = profile_resolver
        self._wall_time_fn = wall_time_fn
        self._monotonic_time_fn = monotonic_time_fn or (lambda: 0.0)

    @property
    def profile(self) -> BodyProfile | None:
        if self.state.body_profile_id is None:
            return None
        return self._resolve_profile(self.state.body_profile_id)

    # --- attach / detach / swap (authoritative; single-statement commits are ---
    # --- already atomic — Store.append_event is one INSERT) ---------------

    def attach(
        self,
        profile_id: str,
        *,
        origin: str = "NORMAL",
        migrated_from_schema_version: str | None = None,
    ) -> None:
        if self.state.attachment_status == "ATTACHED":
            raise AdapterError("already_attached")
        profile = self._resolve_profile(profile_id)
        new_generation = self.state.attachment_generation + 1
        new_instance_id = self.state.body_instance_id or new_id()
        payload: dict[str, Any] = {
            "old_status": self.state.attachment_status,
            "new_status": "ATTACHED",
            "new_body_instance_id": new_instance_id,
            "new_profile_id": profile.profile_id,
            "new_generation": new_generation,
            "profile_schema_version": profile.schema_version,
            "profile_definition_hash": profile_definition_hash(profile),
            "origin": origin,
        }
        if migrated_from_schema_version is not None:
            payload["migrated_from_schema_version"] = migrated_from_schema_version
        self.store.append_event(
            agent_id=self.agent_id,
            event_type="embodiment_body_attached",
            monotonic_time=self._monotonic_time_fn(),
            wall_time=self._wall_time_fn(),
            payload=payload,
        )
        self.state = AttachmentState(
            body_instance_id=new_instance_id,
            body_profile_id=profile.profile_id,
            attachment_status="ATTACHED",
            attachment_generation=new_generation,
        )

    def detach(self, reason: str) -> None:
        if self.state.attachment_status != "ATTACHED":
            raise AdapterError("not_attached")
        old_generation = self.state.attachment_generation
        new_generation = old_generation + 1
        self.store.append_event(
            agent_id=self.agent_id,
            event_type="embodiment_body_detached",
            monotonic_time=self._monotonic_time_fn(),
            wall_time=self._wall_time_fn(),
            payload={
                "body_instance_id": self.state.body_instance_id,
                "profile_id": self.state.body_profile_id,
                "old_generation": old_generation,
                "new_generation": new_generation,
                "reason": reason,
            },
        )
        self.state = AttachmentState(
            body_instance_id=self.state.body_instance_id,
            body_profile_id=None,
            attachment_status="DETACHED",
            attachment_generation=new_generation,
        )

    def swap_profile(self, new_profile_id: str) -> None:
        if self.state.attachment_status != "ATTACHED":
            raise AdapterError("not_attached")
        new_profile = self._resolve_profile(new_profile_id)
        old_generation = self.state.attachment_generation
        new_generation = old_generation + 1
        self.store.append_event(
            agent_id=self.agent_id,
            event_type="embodiment_body_profile_swapped",
            monotonic_time=self._monotonic_time_fn(),
            wall_time=self._wall_time_fn(),
            payload={
                "body_instance_id": self.state.body_instance_id,
                "old_profile_id": self.state.body_profile_id,
                "new_profile_id": new_profile.profile_id,
                "old_generation": old_generation,
                "new_generation": new_generation,
                "profile_schema_version": new_profile.schema_version,
                "profile_definition_hash": profile_definition_hash(new_profile),
            },
        )
        # Compatible swap retains body_instance_id; true replacement is detach+attach.
        self.state = AttachmentState(
            body_instance_id=self.state.body_instance_id,
            body_profile_id=new_profile.profile_id,
            attachment_status="ATTACHED",
            attachment_generation=new_generation,
        )

    # --- execution --------------------------------------------------------

    def execute(
        self,
        request: AdapterRequest,
        embodiment: Embodiment,
        rng: SeededRNG,
    ) -> dict[str, Any]:
        """Validate; on reject return failed raw (no Embodiment.execute); else
        clamp supported continuous parameters (Supplement S1) and delegate the
        translated request — the original `request.params` is never mutated."""
        rejection = self._validate_attachment(request)
        if rejection is not None:
            return rejection
        profile = self.profile
        assert profile is not None  # ATTACHED implies a resolvable profile
        translated_params, provenance, constraint = self._translate_continuous_limits(
            request, profile
        )
        if constraint is not None:
            return self._reject(request, "BODY_LIMIT_REJECTED", constraint, profile=profile)
        raw = embodiment.execute_primitive(request.capability, translated_params, rng)
        raw["body_profile_id"] = self.state.body_profile_id
        raw["profile_definition_hash"] = profile_definition_hash(profile)
        raw["translation_applied"] = provenance is not None
        if provenance is not None:
            raw.update(provenance)
        return raw

    def _validate_attachment(self, request: AdapterRequest) -> dict[str, Any] | None:
        """Non-continuous admission checks: attachment/generation/hash/capability
        support. Continuous physical-limit clamping is `_translate_continuous_limits`."""
        if self.state.attachment_status != "ATTACHED":
            return self._reject(request, "BODY_DETACHED", None)
        if request.attachment_generation != self.state.attachment_generation:
            return self._reject(request, "STALE_ATTACHMENT_GENERATION", None)
        profile = self.profile
        assert profile is not None  # ATTACHED implies a resolvable profile
        if request.expected_profile_hash is not None:
            if request.expected_profile_hash != profile_definition_hash(profile):
                return self._reject(request, "PROFILE_HASH_MISMATCH", None, profile=profile)
        if request.capability not in profile.supported_capabilities:
            return self._reject(request, "UNSUPPORTED_BODY_CAPABILITY", None, profile=profile)
        return None

    def _translate_continuous_limits(
        self, request: AdapterRequest, profile: BodyProfile
    ) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
        """Returns `(translated_params, translation_provenance, reject_constraint)`.

        Exactly one of `translation_provenance` / `reject_constraint` is non-None
        when clamping applied / hard-rejected; both are `None` when the request
        needed no translation. Never mutates `request.params`."""
        if request.capability not in self._CONTINUOUS_STEP_CAPABILITIES:
            return request.params, None, None
        max_step = profile.physical_limits.get("max_step")
        if max_step is None:
            return request.params, None, None
        default_step = 1.2 if request.capability == "RETREAT" else 1.0
        raw_step = request.params.get("step", default_step)
        try:
            requested_step = float(raw_step)
        except (TypeError, ValueError):
            return (
                request.params,
                None,
                {"limit": "max_step", "requested": raw_step, "max": max_step, "reason": "malformed"},
            )
        if not math.isfinite(requested_step):
            return (
                request.params,
                None,
                {
                    "limit": "max_step",
                    "requested": requested_step,
                    "max": max_step,
                    "reason": "non_finite",
                },
            )
        if requested_step <= 0:
            return (
                request.params,
                None,
                {
                    "limit": "max_step",
                    "requested": requested_step,
                    "max": max_step,
                    "reason": "non_positive",
                },
            )
        if requested_step <= max_step:
            return request.params, None, None
        if not bool(profile.physical_limits.get("max_step_clampable", True)):
            return (
                request.params,
                None,
                {
                    "limit": "max_step",
                    "requested": requested_step,
                    "max": max_step,
                    "reason": "non_clampable",
                },
            )
        translated = dict(request.params)
        translated["step"] = max_step
        provenance = {
            "requested_parameters": dict(request.params),
            "applied_parameters": translated,
            "translation_reason": "max_step_exceeded_clamped_to_profile_limit",
        }
        return translated, provenance, None

    def _reject(
        self,
        request: AdapterRequest,
        failure_code: str,
        profile_constraint: Any,
        *,
        profile: BodyProfile | None = None,
    ) -> dict[str, Any]:
        return {
            "ok_raw": False,
            "reason": failure_code,
            "failure_code": failure_code,
            "execution_id": new_id(),
            "request_id": request.request_id,
            "body_instance_id": self.state.body_instance_id,
            "body_profile_id": self.state.body_profile_id,
            "profile_definition_hash": profile_definition_hash(profile) if profile else None,
            "attachment_generation": self.state.attachment_generation,
            "capability": request.capability,
            "profile_constraint": profile_constraint,
            "translation_applied": False,
            "tick": request.tick,
            "adapter_certified": False,
        }
