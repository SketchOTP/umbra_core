"""EmbodimentAdapter — thin governed body-profile constraint enforcement.

Attach/detach/swap append authoritative attachment events. `execute()` validates
a request against the current attachment + body-profile constraints; on success
it delegates the sole world mutation to `Embodiment.execute_primitive`; on
rejection it returns a failed raw result (`ok_raw=False`) without ever touching
`Embodiment` — governance verifies and commits that failed outcome through the
existing `outcome_verified` path exactly like any other executed capability.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

from umbra_core.embodiment import Embodiment
from umbra_core.embodiment_adapters.profiles import BodyProfile, get_profile, profile_definition_hash
from umbra_core.persistence import Store
from umbra_core.util import SeededRNG, new_id

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


class EmbodimentAdapter:
    """Enforces body-profile capability/limit constraints; never grants authority.

    All authoritative world mutation stays inside `Embodiment.execute_primitive`.
    The adapter can only narrow what governance already admitted — it can never
    widen it (see `test_adapter_cannot_grant_capabilities`).
    """

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

    def attach(self, profile_id: str, *, origin: str = "NORMAL") -> None:
        if self.state.attachment_status == "ATTACHED":
            raise AdapterError("already_attached")
        profile = self._resolve_profile(profile_id)
        new_generation = self.state.attachment_generation + 1
        new_instance_id = self.state.body_instance_id or new_id()
        self.store.append_event(
            agent_id=self.agent_id,
            event_type="embodiment_body_attached",
            monotonic_time=self._monotonic_time_fn(),
            wall_time=self._wall_time_fn(),
            payload={
                "old_status": self.state.attachment_status,
                "new_status": "ATTACHED",
                "new_body_instance_id": new_instance_id,
                "new_profile_id": profile.profile_id,
                "new_generation": new_generation,
                "profile_schema_version": profile.schema_version,
                "profile_definition_hash": profile_definition_hash(profile),
                "origin": origin,
            },
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
        """Validate; on reject return failed raw (no Embodiment.execute); else delegate."""
        rejection = self._validate(request)
        if rejection is not None:
            return rejection
        return embodiment.execute_primitive(request.capability, request.params, rng)

    def _validate(self, request: AdapterRequest) -> dict[str, Any] | None:
        if self.state.attachment_status != "ATTACHED":
            return self._reject(request, "BODY_DETACHED", None)
        if request.attachment_generation != self.state.attachment_generation:
            return self._reject(request, "STALE_ATTACHMENT_GENERATION", None)
        profile = self.profile
        assert profile is not None  # ATTACHED implies a resolvable profile
        if request.expected_profile_hash is not None:
            if request.expected_profile_hash != profile_definition_hash(profile):
                return self._reject(request, "PROFILE_HASH_MISMATCH", None)
        if request.capability not in profile.supported_capabilities:
            return self._reject(request, "UNSUPPORTED_BODY_CAPABILITY", None)
        constraint = self._limit_violation(request, profile)
        if constraint is not None:
            return self._reject(request, "BODY_LIMIT_REJECTED", constraint)
        return None

    def _limit_violation(
        self, request: AdapterRequest, profile: BodyProfile
    ) -> dict[str, Any] | None:
        if request.capability in ("MOVE", "APPROACH", "RETREAT"):
            max_step = profile.physical_limits.get("max_step")
            if max_step is None:
                return None
            default_step = 1.2 if request.capability == "RETREAT" else 1.0
            requested_step = float(request.params.get("step", default_step))
            if requested_step > max_step:
                return {
                    "limit": "max_step",
                    "requested": requested_step,
                    "max": max_step,
                }
        return None

    def _reject(
        self,
        request: AdapterRequest,
        failure_code: str,
        profile_constraint: Any,
    ) -> dict[str, Any]:
        return {
            "ok_raw": False,
            "reason": failure_code,
            "failure_code": failure_code,
            "execution_id": new_id(),
            "request_id": request.request_id,
            "body_instance_id": self.state.body_instance_id,
            "body_profile_id": self.state.body_profile_id,
            "attachment_generation": self.state.attachment_generation,
            "capability": request.capability,
            "profile_constraint": profile_constraint,
            "tick": request.tick,
            "adapter_certified": False,
        }
