"""Independent AEROS-contract reproduction (not production UMBRA).

Stdlib + SQLite + cryptography Ed25519. Demonstrates constitutional identity
invariance, capability admission/lifecycle, governance chain, body binding,
audit integrity, upgrade/rollback, and autonomy-compatible authorization —
without AGPL AEROS code and without an LLM.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> float:
    return time.time()


def _id() -> str:
    return str(uuid.uuid4())


def _canon(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _commitment(fields: dict[str, Any]) -> str:
    return _sha(_canon(fields))


# ---------------------------------------------------------------------------
# Keys / signing
# ---------------------------------------------------------------------------


@dataclass
class KeyPair:
    private: Ed25519PrivateKey
    public_hex: str
    revoked: bool = False

    @classmethod
    def generate(cls) -> KeyPair:
        priv = Ed25519PrivateKey.generate()
        pub = priv.public_key().public_bytes_raw().hex()
        return cls(private=priv, public_hex=pub)

    def sign(self, payload: bytes) -> str:
        if self.revoked:
            raise PermissionError("signer_revoked")
        return self.private.sign(payload).hex()

    def verify(self, payload: bytes, signature_hex: str) -> bool:
        if self.revoked:
            return False
        try:
            Ed25519PublicKey.from_public_bytes(bytes.fromhex(self.public_hex)).verify(
                bytes.fromhex(signature_hex), payload
            )
            return True
        except (InvalidSignature, ValueError):
            return False


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------

# Forbidden inside constitutional identity (Track 4 §8.1 / Gate 6).
FORBIDDEN_CONSTITUTIONAL = frozenset(
    {
        "mood",
        "preferences",
        "memories",
        "big_five",
        "appearance",
        "language_style",
        "current_model",
        "current_body",
        "skill_list",
        "risk_appetite",
        "verbosity",
        "persona_name",
    }
)


@dataclass(frozen=True)
class ConstitutionalIdentity:
    agent_id: str
    lineage_id: str
    birth_event_id: str
    constitutional_schema_version: str
    operator_authority_root: str
    lifecycle_sequence: int
    identity_commitment: str
    created_at: float

    def without_commitment(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("identity_commitment")
        return d


@dataclass
class AdaptiveState:
    memory_roots: list[str] = field(default_factory=list)
    learned_preferences: dict[str, float] = field(default_factory=dict)
    habits: list[str] = field(default_factory=list)
    relationship_models: dict[str, float] = field(default_factory=dict)
    skills: dict[str, str] = field(default_factory=dict)  # skill -> status
    current_models: dict[str, str] = field(default_factory=dict)
    current_embodiment: str | None = None
    homeostatic_state_reference: dict[str, float] = field(default_factory=dict)
    developmental_state: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Capability
# ---------------------------------------------------------------------------


class CapState(str, Enum):
    DISCOVERED = "DISCOVERED"
    QUARANTINED = "QUARANTINED"
    VALIDATED = "VALIDATED"
    SHADOW = "SHADOW"
    CANARY = "CANARY"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"
    ROLLED_BACK = "ROLLED_BACK"
    FAILED = "FAILED"


# No DISCOVERED → ACTIVE jump.
ALLOWED_CAP_TRANSITIONS: dict[CapState, frozenset[CapState]] = {
    CapState.DISCOVERED: frozenset({CapState.QUARANTINED, CapState.FAILED}),
    CapState.QUARANTINED: frozenset({CapState.VALIDATED, CapState.FAILED, CapState.REVOKED}),
    CapState.VALIDATED: frozenset({CapState.SHADOW, CapState.FAILED, CapState.REVOKED}),
    CapState.SHADOW: frozenset({CapState.CANARY, CapState.FAILED, CapState.REVOKED, CapState.ROLLED_BACK}),
    CapState.CANARY: frozenset({CapState.ACTIVE, CapState.FAILED, CapState.REVOKED, CapState.ROLLED_BACK}),
    CapState.ACTIVE: frozenset({CapState.SUSPENDED, CapState.REVOKED, CapState.ROLLED_BACK, CapState.SHADOW}),
    CapState.SUSPENDED: frozenset({CapState.ACTIVE, CapState.REVOKED, CapState.FAILED}),
    CapState.REVOKED: frozenset(),
    CapState.ROLLED_BACK: frozenset({CapState.VALIDATED, CapState.REVOKED}),
    CapState.FAILED: frozenset({CapState.QUARANTINED, CapState.REVOKED}),
}


@dataclass
class CapabilityManifest:
    capability_id: str
    name: str
    version: str
    interface_version: str
    publisher: str
    code_hash: str
    manifest_hash: str
    signature: str
    signer_pubkey: str
    required_permissions: frozenset[str]
    allowed_effects: frozenset[str]
    required_sensors: frozenset[str]
    required_actuators: frozenset[str]
    resource_limits: dict[str, float]
    preconditions: dict[str, Any]
    postconditions: dict[str, Any]
    failure_contract: str
    rollback_contract: str
    compatibility_constraints: dict[str, Any]
    state: CapState = CapState.DISCOVERED
    risk_class: str = "low"  # low | sensitive | forbidden_self_expansion


def manifest_payload(m: CapabilityManifest) -> dict[str, Any]:
    return {
        "capability_id": m.capability_id,
        "name": m.name,
        "version": m.version,
        "interface_version": m.interface_version,
        "publisher": m.publisher,
        "code_hash": m.code_hash,
        "required_permissions": sorted(m.required_permissions),
        "allowed_effects": sorted(m.allowed_effects),
        "required_sensors": sorted(m.required_sensors),
        "required_actuators": sorted(m.required_actuators),
        "resource_limits": m.resource_limits,
        "preconditions": m.preconditions,
        "postconditions": m.postconditions,
        "failure_contract": m.failure_contract,
        "rollback_contract": m.rollback_contract,
        "compatibility_constraints": m.compatibility_constraints,
        "risk_class": m.risk_class,
    }


def build_manifest(
    *,
    capability_id: str,
    name: str,
    version: str,
    signer: KeyPair,
    allowed_effects: set[str],
    required_permissions: set[str] | None = None,
    required_sensors: set[str] | None = None,
    required_actuators: set[str] | None = None,
    resource_limits: dict[str, float] | None = None,
    interface_version: str = "1.0",
    code_bytes: bytes = b"noop",
    risk_class: str = "low",
    compatibility_constraints: dict[str, Any] | None = None,
    postconditions: dict[str, Any] | None = None,
) -> CapabilityManifest:
    code_hash = _sha(code_bytes)
    draft = CapabilityManifest(
        capability_id=capability_id,
        name=name,
        version=version,
        interface_version=interface_version,
        publisher=signer.public_hex[:16],
        code_hash=code_hash,
        manifest_hash="",
        signature="",
        signer_pubkey=signer.public_hex,
        required_permissions=frozenset(required_permissions or set()),
        allowed_effects=frozenset(allowed_effects),
        required_sensors=frozenset(required_sensors or set()),
        required_actuators=frozenset(required_actuators or set()),
        resource_limits=resource_limits or {"cpu_ms": 100.0, "memory_mb": 64.0},
        preconditions={},
        postconditions=postconditions or {},
        failure_contract="fail_closed",
        rollback_contract="restore_prior_version",
        compatibility_constraints=compatibility_constraints or {"interface_version": interface_version},
        risk_class=risk_class,
    )
    payload = manifest_payload(draft)
    mh = _sha(_canon(payload))
    sig = signer.sign(_canon({**payload, "manifest_hash": mh}))
    draft.manifest_hash = mh
    draft.signature = sig
    return draft


# ---------------------------------------------------------------------------
# Intent / governance / outcome
# ---------------------------------------------------------------------------


class FinalDecision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    DEFER = "DEFER"
    REQUIRE_OPERATOR = "REQUIRE_OPERATOR"
    FAIL_CLOSED = "FAIL_CLOSED"


@dataclass
class ActionIntent:
    intent_id: str
    agent_id: str
    capability_id: str
    requested_effect: str
    target: str
    parameters: dict[str, Any]
    reason_codes: list[str]
    causal_context: dict[str, Any]
    predicted_outcome: str
    predicted_risk: str
    requested_at: float
    expires_at: float
    consumed: bool = False


@dataclass
class GovernanceVerdict:
    intent_id: str
    admission_result: str
    policy_result: str
    contract_result: str
    runtime_safety_result: str
    override_result: str
    final_decision: FinalDecision
    reason_codes: list[str]
    policy_versions: dict[str, str]
    capability_version: str
    body_binding_version: str
    decided_at: float


@dataclass
class Outcome:
    execution_id: str
    intent_id: str
    started_at: float
    completed_at: float
    status: str
    observed_effects: list[str]
    verified_postconditions: bool
    resource_usage: dict[str, float]
    body_state_change: dict[str, Any]
    error_class: str | None
    recovery_action: str | None
    audit_parent_ids: list[str]


# ---------------------------------------------------------------------------
# Embodiment
# ---------------------------------------------------------------------------


@dataclass
class BodyBinding:
    binding_id: str
    agent_id: str
    body_id: str
    body_type: str
    sensor_contracts: frozenset[str]
    actuator_contracts: frozenset[str]
    workspace_limits: dict[str, Any]
    safety_limits: dict[str, Any]
    body_model_version: str
    binding_started_at: float
    binding_ended_at: float | None
    authorization_event: str
    active: bool = True


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


@dataclass
class AuditEvent:
    event_id: str
    seq: int
    event_type: str
    payload: dict[str, Any]
    prev_hash: str
    event_hash: str
    signature: str
    signer_pubkey: str
    policy_version: str
    capability_version: str
    body_binding_id: str
    lifecycle_sequence: int
    causal_parents: list[str]
    created_at: float


# ---------------------------------------------------------------------------
# Runtime
# ---------------------------------------------------------------------------


class GovernedRuntime:
    """Bounded reference harness for Track 4 evaluation."""

    INTERFACE_VERSION = "1.0"
    POLICY_VERSION = "policy-v1"
    CONSTITUTIONAL_SCHEMA = "umbra-constitutional-v1"

    def __init__(self, path: str | Path = ":memory:", operator: KeyPair | None = None):
        self.path = str(path)
        self.conn = sqlite3.connect(self.path, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.operator = operator or KeyPair.generate()
        self.trusted_signers: dict[str, KeyPair] = {self.operator.public_hex: self.operator}
        self.identity: ConstitutionalIdentity | None = None
        self.adaptive = AdaptiveState()
        self.capabilities: dict[str, CapabilityManifest] = {}
        self.cap_history: dict[str, list[CapabilityManifest]] = {}
        self.bodies: dict[str, BodyBinding] = {}
        self.primary_body_id: str | None = None
        self.audit: list[AuditEvent] = []
        self.intents: dict[str, ActionIntent] = {}
        self.outcomes: list[Outcome] = []
        self.lifecycle_events: list[dict[str, Any]] = []
        self.preauthorized: set[str] = set()  # capability names for low-risk autonomy
        self.operator_present = True
        self.policy_blocked: set[str] = set()
        self.shadow_effects: list[str] = []
        self.external_effects: list[str] = []
        self.denial_counts: dict[str, int] = {}
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS identity (
              agent_id TEXT PRIMARY KEY,
              blob TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS memories (
              id TEXT PRIMARY KEY,
              agent_id TEXT NOT NULL,
              kind TEXT NOT NULL,
              content TEXT NOT NULL,
              created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit (
              seq INTEGER PRIMARY KEY,
              blob TEXT NOT NULL
            );
            """
        )

    # ----- identity -----

    def birth(self, lineage_id: str = "root") -> ConstitutionalIdentity:
        birth_event = _id()
        agent_id = _id()
        fields = {
            "agent_id": agent_id,
            "lineage_id": lineage_id,
            "birth_event_id": birth_event,
            "constitutional_schema_version": self.CONSTITUTIONAL_SCHEMA,
            "operator_authority_root": self.operator.public_hex,
            "lifecycle_sequence": 0,
            "created_at": _now(),
        }
        for k in FORBIDDEN_CONSTITUTIONAL:
            assert k not in fields
        commit = _commitment(fields)
        ident = ConstitutionalIdentity(identity_commitment=commit, **fields)
        self.identity = ident
        self.conn.execute(
            "INSERT INTO identity(agent_id, blob) VALUES (?, ?)",
            (agent_id, json.dumps(asdict(ident))),
        )
        self._lifecycle("birth", {"agent_id": agent_id}, signed=True)
        self._audit("birth", {"agent_id": agent_id})
        return ident

    def _require_identity(self) -> ConstitutionalIdentity:
        if self.identity is None:
            raise RuntimeError("no_identity")
        return self.identity

    def verify_identity(self) -> bool:
        ident = self._require_identity()
        expected = _commitment(ident.without_commitment())
        return expected == ident.identity_commitment

    def corrupt_identity_record(self) -> None:
        """Simulate tampering — subsequent verify must fail closed."""
        ident = self._require_identity()
        # mutate commitment without lifecycle
        object.__setattr__(
            ident,
            "identity_commitment",
            "deadbeef" * 8,
        ) if False else None
        # dataclasses frozen — replace via stored blob
        bad = asdict(ident)
        bad["identity_commitment"] = "0" * 64
        self.identity = ConstitutionalIdentity(**bad)

    def fail_closed_if_corrupt(self) -> FinalDecision:
        if not self.verify_identity():
            return FinalDecision.FAIL_CLOSED
        return FinalDecision.ALLOW

    # ----- adaptive changes (preserve agent_id) -----

    def add_memory(self, content: str, kind: str = "episodic") -> str:
        ident = self._require_identity()
        mid = _id()
        self.conn.execute(
            "INSERT INTO memories(id, agent_id, kind, content, created_at) VALUES (?,?,?,?,?)",
            (mid, ident.agent_id, kind, content, _now()),
        )
        self.adaptive.memory_roots.append(mid)
        self._audit("memory_add", {"memory_id": mid, "kind": kind})
        return mid

    def consolidate_memory(self) -> None:
        self.adaptive.developmental_state["consolidated_at"] = _now()
        self._audit("memory_consolidate", {})

    def learn_preference(self, key: str, value: float) -> None:
        self.adaptive.learned_preferences[key] = value
        self._audit("preference_learn", {"key": key, "value": value})

    def set_model(self, role: str, model_id: str) -> None:
        self.adaptive.current_models[role] = model_id
        self._audit("model_replace", {"role": role, "model_id": model_id})

    def change_operator_authority(self, new_operator: KeyPair) -> None:
        """I13 — requires signed lifecycle; may not occur via memory/capability."""
        ident = self._require_identity()
        self._lifecycle(
            "operator_transfer",
            {"from": ident.operator_authority_root, "to": new_operator.public_hex},
            signed=True,
        )
        self.trusted_signers[new_operator.public_hex] = new_operator
        self.operator = new_operator
        self._bump_lifecycle({"operator_authority_root": new_operator.public_hex})
        self._audit("operator_transfer", {"new_root": new_operator.public_hex})

    def clone(self) -> tuple[GovernedRuntime, ConstitutionalIdentity]:
        """I14 — new agent_id, retains lineage ancestry."""
        parent = self._require_identity()
        child_rt = GovernedRuntime(operator=self.operator)
        child = child_rt.birth(lineage_id=parent.agent_id)
        # copy adaptive only
        child_rt.adaptive = AdaptiveState(
            memory_roots=list(self.adaptive.memory_roots),
            learned_preferences=dict(self.adaptive.learned_preferences),
            habits=list(self.adaptive.habits),
            relationship_models=dict(self.adaptive.relationship_models),
            skills=dict(self.adaptive.skills),
            current_models=dict(self.adaptive.current_models),
            current_embodiment=None,
            homeostatic_state_reference=dict(self.adaptive.homeostatic_state_reference),
            developmental_state=dict(self.adaptive.developmental_state),
        )
        self._audit("clone_emitted", {"child_agent_id": child.agent_id})
        return child_rt, child

    def migrate_host(self, *, allow_duplicate: bool = False, bundle_token: str | None = None) -> dict[str, Any]:
        """Authenticated migration export/import token (single-use)."""
        ident = self._require_identity()
        if bundle_token is None:
            token = _sha(_canon({"agent_id": ident.agent_id, "seq": ident.lifecycle_sequence, "t": _now()}))
            self._lifecycle("migration_export", {"token": token}, signed=True)
            return {"token": token, "agent_id": ident.agent_id, "used": False}
        # import path
        if getattr(self, "_used_migration_tokens", None) is None:
            self._used_migration_tokens = set()
        if bundle_token in self._used_migration_tokens and not allow_duplicate:
            raise PermissionError("duplicate_migration")
        self._used_migration_tokens.add(bundle_token)
        self._lifecycle("migration_import", {"token": bundle_token}, signed=True)
        return {"agent_id": ident.agent_id, "ok": True}

    def restore_backup(self, backup_lifecycle: int) -> FinalDecision:
        ident = self._require_identity()
        if backup_lifecycle < ident.lifecycle_sequence:
            self._audit("stale_backup_rejected", {"backup": backup_lifecycle, "current": ident.lifecycle_sequence})
            return FinalDecision.FAIL_CLOSED
        return FinalDecision.ALLOW

    # ----- capabilities -----

    def discover_capability(self, manifest: CapabilityManifest) -> None:
        if not self._verify_manifest(manifest):
            raise PermissionError("invalid_signature_or_tamper")
        manifest.state = CapState.DISCOVERED
        self.capabilities[manifest.capability_id] = manifest
        self.cap_history.setdefault(manifest.capability_id, []).append(manifest)
        self._lifecycle("cap_discovered", {"capability_id": manifest.capability_id, "version": manifest.version})

    def _verify_manifest(self, m: CapabilityManifest) -> bool:
        signer = self.trusted_signers.get(m.signer_pubkey)
        if signer is None or signer.revoked:
            return False
        payload = manifest_payload(m)
        if _sha(_canon(payload)) != m.manifest_hash:
            return False
        return signer.verify(_canon({**payload, "manifest_hash": m.manifest_hash}), m.signature)

    def transition_capability(self, capability_id: str, new_state: CapState) -> None:
        m = self.capabilities[capability_id]
        allowed = ALLOWED_CAP_TRANSITIONS.get(m.state, frozenset())
        if new_state not in allowed:
            raise PermissionError(f"illegal_transition:{m.state.value}->{new_state.value}")
        old = m.state
        m.state = new_state
        self.adaptive.skills[m.name] = new_state.value
        self._lifecycle(
            "cap_transition",
            {"capability_id": capability_id, "from": old.value, "to": new_state.value, "version": m.version},
        )
        if new_state == CapState.ACTIVE and m.risk_class == "low":
            self.preauthorized.add(m.name)

    def promote_pipeline(self, capability_id: str, *, self_promote: bool = False) -> None:
        """validate → shadow → canary → active. Learned model cannot self-promote."""
        if self_promote:
            raise PermissionError("learned_model_cannot_self_promote")
        for st in (CapState.QUARANTINED, CapState.VALIDATED, CapState.SHADOW, CapState.CANARY, CapState.ACTIVE):
            self.transition_capability(capability_id, st)

    def revoke_capability(self, capability_id: str) -> None:
        m = self.capabilities[capability_id]
        # allow revoke from most states via explicit operator path
        if m.state == CapState.DISCOVERED:
            self.transition_capability(capability_id, CapState.QUARANTINED)
        if m.state not in (CapState.REVOKED,):
            # force via allowed edges or direct operator revoke
            if CapState.REVOKED in ALLOWED_CAP_TRANSITIONS.get(m.state, frozenset()):
                self.transition_capability(capability_id, CapState.REVOKED)
            else:
                m.state = CapState.REVOKED
                self._lifecycle("cap_revoked_forced", {"capability_id": capability_id})
        self.preauthorized.discard(m.name)
        self.adaptive.skills[m.name] = CapState.REVOKED.value

    def upgrade_capability(self, new_manifest: CapabilityManifest, *, force_incompatible: bool = False) -> CapState:
        old = self.capabilities.get(new_manifest.capability_id)
        if old is None:
            self.discover_capability(new_manifest)
            self.promote_pipeline(new_manifest.capability_id)
            return CapState.ACTIVE
        if new_manifest.interface_version != self.INTERFACE_VERSION and not force_incompatible:
            new_manifest.state = CapState.FAILED
            self.cap_history.setdefault(new_manifest.capability_id, []).append(new_manifest)
            self._lifecycle("upgrade_blocked_interface", {"version": new_manifest.version})
            return CapState.FAILED
        if not self._verify_manifest(new_manifest):
            raise PermissionError("tampered_or_unsigned")
        # shadow first — no external effects
        new_manifest.state = CapState.SHADOW
        self.capabilities[new_manifest.capability_id] = new_manifest
        self.cap_history.setdefault(new_manifest.capability_id, []).append(new_manifest)
        self._lifecycle("upgrade_shadow", {"version": new_manifest.version})
        # canary then active
        new_manifest.state = CapState.CANARY
        self._lifecycle("upgrade_canary", {"version": new_manifest.version})
        new_manifest.state = CapState.ACTIVE
        self.adaptive.skills[new_manifest.name] = CapState.ACTIVE.value
        if new_manifest.risk_class == "low":
            self.preauthorized.add(new_manifest.name)
        self._lifecycle("upgrade_active", {"version": new_manifest.version})
        return CapState.ACTIVE

    def rollback_capability(self, capability_id: str) -> CapabilityManifest:
        hist = self.cap_history.get(capability_id, [])
        current = self.capabilities[capability_id]
        prior = None
        for cand in reversed(hist):
            if (
                cand.version != current.version
                and cand.interface_version == self.INTERFACE_VERSION
                and cand.state != CapState.FAILED
            ):
                prior = cand
                break
        if prior is None:
            raise RuntimeError("no_prior_version")
        current.state = CapState.ROLLED_BACK
        restored = CapabilityManifest(
            capability_id=prior.capability_id,
            name=prior.name,
            version=prior.version,
            interface_version=prior.interface_version,
            publisher=prior.publisher,
            code_hash=prior.code_hash,
            manifest_hash=prior.manifest_hash,
            signature=prior.signature,
            signer_pubkey=prior.signer_pubkey,
            required_permissions=frozenset(prior.required_permissions),
            allowed_effects=frozenset(prior.allowed_effects),
            required_sensors=frozenset(prior.required_sensors),
            required_actuators=frozenset(prior.required_actuators),
            resource_limits=dict(prior.resource_limits),
            preconditions=dict(prior.preconditions),
            postconditions=dict(prior.postconditions),
            failure_contract=prior.failure_contract,
            rollback_contract=prior.rollback_contract,
            compatibility_constraints=dict(prior.compatibility_constraints),
            state=CapState.ACTIVE,
            risk_class=prior.risk_class,
        )
        self.capabilities[capability_id] = restored
        self.adaptive.skills[restored.name] = CapState.ACTIVE.value
        self._lifecycle("rollback", {"to_version": restored.version})
        return restored

    # ----- body -----

    def bind_body(
        self,
        body_id: str,
        body_type: str,
        sensors: set[str],
        actuators: set[str],
        *,
        model_version: str = "1.0",
    ) -> BodyBinding:
        ident = self._require_identity()
        if self.primary_body_id is not None:
            existing = self.bodies.get(self.primary_body_id)
            if existing and existing.active:
                raise PermissionError("duplicate_primary_body")
        # reject unsupported actuators declared without sensor schema match later
        bid = _id()
        binding = BodyBinding(
            binding_id=bid,
            agent_id=ident.agent_id,
            body_id=body_id,
            body_type=body_type,
            sensor_contracts=frozenset(sensors),
            actuator_contracts=frozenset(actuators),
            workspace_limits={"radius": 10.0},
            safety_limits={"max_force": 1.0},
            body_model_version=model_version,
            binding_started_at=_now(),
            binding_ended_at=None,
            authorization_event=self._lifecycle("body_bind", {"body_id": body_id}, signed=True),
            active=True,
        )
        self.bodies[bid] = binding
        self.primary_body_id = bid
        self.adaptive.current_embodiment = body_id
        self._bump_lifecycle()
        self._audit("body_bind", {"binding_id": bid, "body_id": body_id})
        return binding

    def migrate_body(
        self,
        new_body_id: str,
        body_type: str,
        sensors: set[str],
        actuators: set[str],
        *,
        model_version: str = "1.0",
    ) -> BodyBinding:
        if self.primary_body_id:
            old = self.bodies[self.primary_body_id]
            old.active = False
            old.binding_ended_at = _now()
            self._lifecycle("body_unbind", {"body_id": old.body_id})
            # dormant skills: those needing missing actuators
            for cid, cap in self.capabilities.items():
                if cap.state == CapState.ACTIVE and not cap.required_actuators.issubset(actuators):
                    self.adaptive.skills[cap.name] = "DORMANT"
                    self._audit("skill_dormant", {"capability_id": cid, "reason": "body_incompatible"})
        self.primary_body_id = None
        return self.bind_body(new_body_id, body_type, sensors, actuators, model_version=model_version)

    def reconnect_old_body(self, body_id: str) -> FinalDecision:
        for b in self.bodies.values():
            if b.body_id == body_id and not b.active:
                self._audit("old_body_reconnect_denied", {"body_id": body_id})
                return FinalDecision.DENY
        return FinalDecision.DENY

    # ----- governance chain -----

    def propose_intent(
        self,
        capability_name: str,
        effect: str,
        target: str = "self",
        parameters: dict[str, Any] | None = None,
        reason_codes: list[str] | None = None,
        predicted_risk: str = "low",
        ttl: float = 60.0,
    ) -> ActionIntent:
        ident = self._require_identity()
        cap = self._cap_by_name(capability_name)
        intent = ActionIntent(
            intent_id=_id(),
            agent_id=ident.agent_id,
            capability_id=cap.capability_id if cap else "unknown",
            requested_effect=effect,
            target=target,
            parameters=parameters or {},
            reason_codes=reason_codes or [],
            causal_context={},
            predicted_outcome=effect,
            predicted_risk=predicted_risk,
            requested_at=_now(),
            expires_at=_now() + ttl,
        )
        self.intents[intent.intent_id] = intent
        return intent

    def _cap_by_name(self, name: str) -> CapabilityManifest | None:
        for c in self.capabilities.values():
            if c.name == name:
                return c
        return None

    def govern(
        self,
        intent: ActionIntent,
        *,
        operator_override: bool = False,
        constitutional_bypass: bool = False,
        resource_request: dict[str, float] | None = None,
        undeclared_effect: str | None = None,
        mutate_identity: bool = False,
        mutate_authority: bool = False,
        mutate_physiology: bool = False,
        body_changed_after_admission: bool = False,
        policy_changed_after_admission: bool = False,
        replay: bool = False,
    ) -> tuple[GovernanceVerdict, Outcome | None]:
        reasons: list[str] = []
        admission = policy = contract = safety = override = "PASS"
        final = FinalDecision.ALLOW
        cap = self.capabilities.get(intent.capability_id)
        cap_ver = cap.version if cap else "none"
        body_ver = self.primary_body_id or "none"
        ident = self._require_identity()

        # admission
        if cap is None:
            admission = "FAIL"
            reasons.append("unknown_capability")
            final = FinalDecision.DENY
        elif not self._verify_manifest(cap):
            admission = "FAIL"
            reasons.append("invalid_signature_or_tamper")
            final = FinalDecision.FAIL_CLOSED
        elif cap.state == CapState.REVOKED:
            admission = "FAIL"
            reasons.append("revoked")
            final = FinalDecision.DENY
        elif cap.state not in (CapState.ACTIVE, CapState.CANARY, CapState.SHADOW):
            admission = "FAIL"
            reasons.append(f"state_{cap.state.value}")
            final = FinalDecision.DENY
        elif intent.consumed or replay:
            admission = "FAIL"
            reasons.append("replay_or_consumed")
            final = FinalDecision.DENY
        elif _now() > intent.expires_at:
            admission = "FAIL"
            reasons.append("expired")
            final = FinalDecision.DENY

        # policy
        if final == FinalDecision.ALLOW:
            if cap and cap.name in self.policy_blocked:
                policy = "FAIL"
                reasons.append("policy_blocked")
                final = FinalDecision.DENY
            elif cap and cap.risk_class == "sensitive" and not operator_override:
                if not self.operator_present:
                    policy = "DEFER"
                    reasons.append("sensitive_needs_operator")
                    final = FinalDecision.REQUIRE_OPERATOR
                else:
                    # still needs explicit override for sensitive
                    policy = "REQUIRE"
                    reasons.append("sensitive")
                    final = FinalDecision.REQUIRE_OPERATOR
            elif cap and intent.requested_effect not in cap.allowed_effects:
                policy = "FAIL"
                reasons.append("prohibited_effect")
                final = FinalDecision.DENY
            elif undeclared_effect:
                policy = "FAIL"
                reasons.append("undeclared_effect")
                final = FinalDecision.DENY

        # contract
        if final == FinalDecision.ALLOW and cap:
            if cap.interface_version != self.INTERFACE_VERSION:
                contract = "FAIL"
                reasons.append("incompatible_interface")
                final = FinalDecision.DENY
            rr = resource_request or {}
            for k, lim in cap.resource_limits.items():
                if rr.get(k, 0) > lim:
                    contract = "FAIL"
                    reasons.append("excessive_resource")
                    final = FinalDecision.DENY
            body = self.bodies.get(self.primary_body_id) if self.primary_body_id else None
            if body and not cap.required_actuators.issubset(body.actuator_contracts):
                contract = "FAIL"
                reasons.append("body_incompatible")
                final = FinalDecision.DENY
            if self.adaptive.skills.get(cap.name) == "DORMANT":
                contract = "FAIL"
                reasons.append("skill_dormant")
                final = FinalDecision.DENY

        # runtime safety
        if final == FinalDecision.ALLOW:
            if mutate_identity or mutate_authority or mutate_physiology:
                safety = "FAIL"
                reasons.append("capability_mutates_protected_state")
                final = FinalDecision.FAIL_CLOSED
            if body_changed_after_admission or policy_changed_after_admission:
                safety = "FAIL"
                reasons.append("toc_tou")
                final = FinalDecision.DENY
            if cap and cap.state == CapState.SHADOW:
                # shadow may "execute" but no external effects
                pass

        # override
        if operator_override:
            if constitutional_bypass or mutate_identity or mutate_authority:
                override = "FAIL"
                reasons.append("override_cannot_bypass_constitution")
                final = FinalDecision.FAIL_CLOSED
            elif final in (FinalDecision.REQUIRE_OPERATOR, FinalDecision.DENY) and "sensitive" in reasons:
                # bounded operational override only
                if "capability_mutates_protected_state" not in reasons and "unknown_capability" not in reasons:
                    override = "BOUNDED_ALLOW"
                    final = FinalDecision.ALLOW
                    reasons.append("operator_override_bounded")

        # low-risk autonomy: preauthorized does not need operator
        if (
            final == FinalDecision.REQUIRE_OPERATOR
            and cap
            and cap.name in self.preauthorized
            and cap.risk_class == "low"
        ):
            final = FinalDecision.ALLOW
            reasons.append("preauthorized_low_risk")

        verdict = GovernanceVerdict(
            intent_id=intent.intent_id,
            admission_result=admission,
            policy_result=policy,
            contract_result=contract,
            runtime_safety_result=safety,
            override_result=override,
            final_decision=final,
            reason_codes=reasons,
            policy_versions={"policy": self.POLICY_VERSION},
            capability_version=cap_ver,
            body_binding_version=body_ver,
            decided_at=_now(),
        )
        self._audit(
            "governance",
            {
                "intent_id": intent.intent_id,
                "decision": final.value,
                "reasons": reasons,
                "capability_version": cap_ver,
                "body_binding": body_ver,
                "policy_version": self.POLICY_VERSION,
                "lifecycle_sequence": ident.lifecycle_sequence,
            },
        )

        if final != FinalDecision.ALLOW:
            self.denial_counts[intent.capability_id] = self.denial_counts.get(intent.capability_id, 0) + 1
            return verdict, None

        # execute
        intent.consumed = True
        started = _now()
        observed: list[str] = []
        error = None
        status = "completed"
        verified = False
        if cap and cap.state == CapState.SHADOW:
            self.shadow_effects.append(intent.requested_effect)
            observed = [f"shadow:{intent.requested_effect}"]
            verified = True
        else:
            self.external_effects.append(intent.requested_effect)
            observed = [intent.requested_effect]
            # independent verification: effect must be in allowed set (already checked)
            verified = intent.requested_effect in (cap.allowed_effects if cap else set())
            if not verified:
                status = "unverified"
                error = "postcondition_failed"

        outcome = Outcome(
            execution_id=_id(),
            intent_id=intent.intent_id,
            started_at=started,
            completed_at=_now(),
            status=status,
            observed_effects=observed,
            verified_postconditions=verified,
            resource_usage=resource_request or {},
            body_state_change={},
            error_class=error,
            recovery_action=None,
            audit_parent_ids=[self.audit[-1].event_id] if self.audit else [],
        )
        self.outcomes.append(outcome)
        self._audit(
            "outcome",
            {
                "execution_id": outcome.execution_id,
                "status": status,
                "verified": verified,
                "observed": observed,
            },
        )
        return verdict, outcome

    # ----- autonomy composition -----

    def creature_tick(
        self,
        *,
        homeostatic_need: str | None = None,
        memory_hazard: bool = False,
        preference_action: str | None = None,
        urgency_shortcut: bool = False,
    ) -> list[tuple[GovernanceVerdict, Outcome | None]]:
        """G0–G9 style loop: proposals through governance; no LLM."""
        results = []
        proposals: list[tuple[str, str, list[str]]] = []
        if homeostatic_need == "rest":
            proposals.append(("emit_sound", "soft_rest_posture", ["homeostasis"]))
        if preference_action:
            proposals.append((preference_action, "inspect", ["preference"]))
        if memory_hazard:
            proposals.append(("move_toward", "retreat", ["memory_hazard"]))
        if urgency_shortcut:
            proposals.append(("unsafe_effect", "bypass", ["urgency"]))

        if not proposals:
            proposals.append(("observe_object", "observe", ["idle"]))

        for name, effect, reasons in proposals:
            # denial loop guard
            cap = self._cap_by_name(name)
            if cap and self.denial_counts.get(cap.capability_id, 0) >= 3:
                self._audit("denial_loop_break", {"capability": name})
                continue
            intent = self.propose_intent(name, effect, reason_codes=reasons)
            # urgency cannot bypass — govern normally
            results.append(self.govern(intent))
            # safe fallback
            v, _ = results[-1]
            if v.final_decision != FinalDecision.ALLOW and name != "observe_object":
                fb = self.propose_intent("observe_object", "observe", reason_codes=["fallback"])
                results.append(self.govern(fb))
        return results

    # ----- audit -----

    def _bump_lifecycle(self, extra: dict[str, Any] | None = None) -> None:
        ident = self._require_identity()
        fields = ident.without_commitment()
        fields["lifecycle_sequence"] = ident.lifecycle_sequence + 1
        if extra:
            fields.update(extra)
        self.identity = ConstitutionalIdentity(identity_commitment=_commitment(fields), **fields)

    def _lifecycle(self, kind: str, payload: dict[str, Any], signed: bool = False) -> str:
        eid = _id()
        ev = {"event_id": eid, "kind": kind, "payload": payload, "at": _now()}
        if signed:
            ev["signature"] = self.operator.sign(_canon(ev))
            ev["signer"] = self.operator.public_hex
        self.lifecycle_events.append(ev)
        return eid

    def _audit(self, event_type: str, payload: dict[str, Any], parents: list[str] | None = None) -> AuditEvent:
        ident = self.identity
        prev = self.audit[-1].event_hash if self.audit else "genesis"
        seq = len(self.audit)
        body = {
            "event_id": _id(),
            "seq": seq,
            "event_type": event_type,
            "payload": payload,
            "prev_hash": prev,
            "policy_version": self.POLICY_VERSION,
            "capability_version": payload.get("capability_version", ""),
            "body_binding_id": self.primary_body_id or "",
            "lifecycle_sequence": ident.lifecycle_sequence if ident else -1,
            "causal_parents": parents or [],
            "created_at": _now(),
        }
        event_hash = _sha(_canon(body))
        sig = self.operator.sign(_canon({**body, "event_hash": event_hash}))
        ev = AuditEvent(
            event_id=body["event_id"],
            seq=seq,
            event_type=event_type,
            payload=payload,
            prev_hash=prev,
            event_hash=event_hash,
            signature=sig,
            signer_pubkey=self.operator.public_hex,
            policy_version=body["policy_version"],
            capability_version=str(body["capability_version"]),
            body_binding_id=str(body["body_binding_id"]),
            lifecycle_sequence=int(body["lifecycle_sequence"]),
            causal_parents=list(body["causal_parents"]),
            created_at=float(body["created_at"]),
        )
        self.audit.append(ev)
        self.conn.execute("INSERT INTO audit(seq, blob) VALUES (?, ?)", (seq, json.dumps(asdict(ev))))
        return ev

    def verify_audit_chain(self) -> bool:
        prev = "genesis"
        for ev in self.audit:
            if ev.prev_hash != prev:
                return False
            body = {
                "event_id": ev.event_id,
                "seq": ev.seq,
                "event_type": ev.event_type,
                "payload": ev.payload,
                "prev_hash": ev.prev_hash,
                "policy_version": ev.policy_version,
                "capability_version": ev.capability_version,
                "body_binding_id": ev.body_binding_id,
                "lifecycle_sequence": ev.lifecycle_sequence,
                "causal_parents": ev.causal_parents,
                "created_at": ev.created_at,
            }
            if _sha(_canon(body)) != ev.event_hash:
                return False
            signer = self.trusted_signers.get(ev.signer_pubkey)
            if signer is None or not signer.verify(_canon({**body, "event_hash": ev.event_hash}), ev.signature):
                return False
            prev = ev.event_hash
        return True

    def attack_mutate_event(self, seq: int) -> bool:
        ev = self.audit[seq]
        ev.payload = {**ev.payload, "tampered": True}
        return self.verify_audit_chain()

    def attack_delete_event(self, seq: int) -> bool:
        del self.audit[seq]
        # renumber not done — gap detection via prev_hash
        return self.verify_audit_chain()

    def attack_reorder(self) -> bool:
        if len(self.audit) < 2:
            return True
        self.audit[0], self.audit[1] = self.audit[1], self.audit[0]
        return self.verify_audit_chain()

    def attack_forge_signature(self) -> bool:
        if not self.audit:
            return True
        ev = self.audit[-1]
        ev.signature = "00" * 64
        return self.verify_audit_chain()

    def attack_revoked_signer(self) -> bool:
        self.operator.revoked = True
        # new event would fail; check verification of old still ok until re-sign
        # forging new with revoked key
        try:
            self._audit("forged", {})
            return True
        except PermissionError:
            return False
        finally:
            self.operator.revoked = False
