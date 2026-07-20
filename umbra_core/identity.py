"""Constitutional identity — immutable birth record; excludes adaptive state."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from umbra_core.util import SCHEMA_VERSION, canon_json, new_id, sha256_hex

# Fields that must never appear in constitutional identity.
FORBIDDEN_IDENTITY_FIELDS = frozenset(
    {
        "personality",
        "memories",
        "model",
        "body",
        "skills",
        "preferences",
        "mood",
        "physiology",
        "energy",
        "fatigue",
        "integrity",
        "stimulation",
        "big_five",
        "current_model",
        "current_body",
        "risk_appetite",
        "verbosity",
        "persona_name",
        "learned_preferences",
    }
)


class IdentityError(Exception):
    """Fail-closed identity / commitment failure."""


@dataclass(frozen=True)
class ConstitutionalIdentity:
    agent_id: str
    lineage_id: str
    birth_event_id: str
    schema_version: str
    created_at: float
    lifecycle_sequence: int
    identity_commitment: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def commitment_payload(self) -> dict[str, Any]:
        d = self.as_dict()
        d.pop("identity_commitment")
        return d


def compute_commitment(fields: dict[str, Any]) -> str:
    clean = {k: v for k, v in fields.items() if k != "identity_commitment"}
    for k in clean:
        if k in FORBIDDEN_IDENTITY_FIELDS:
            raise IdentityError(f"forbidden_constitutional_field:{k}")
    return sha256_hex(canon_json(clean))


def deterministic_id(seed: int, label: str) -> str:
    """Stable UUID-shaped id from seed (replay/restart continuity)."""
    h = sha256_hex(f"umbra:{label}:{seed}")
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def create_birth(
    *,
    created_at: float,
    lineage_id: str | None = None,
    agent_id: str | None = None,
    birth_event_id: str | None = None,
    seed: int | None = None,
) -> ConstitutionalIdentity:
    if agent_id is None and seed is not None:
        aid = deterministic_id(seed, "agent")
    else:
        aid = agent_id or new_id()
    lid = lineage_id or aid
    if birth_event_id is None and seed is not None:
        bid = deterministic_id(seed, "birth")
    else:
        bid = birth_event_id or new_id()
    # Seed-driven births freeze created_at for commitment stability across machines.
    created = (1_700_000_000.0 + float(seed) * 1e-6) if seed is not None else float(created_at)
    payload = {
        "agent_id": aid,
        "lineage_id": lid,
        "birth_event_id": bid,
        "schema_version": SCHEMA_VERSION,
        "created_at": created,
        "lifecycle_sequence": 0,
    }
    commitment = compute_commitment(payload)
    return ConstitutionalIdentity(identity_commitment=commitment, **payload)


def verify_identity(ident: ConstitutionalIdentity) -> None:
    expected = compute_commitment(ident.commitment_payload())
    if expected != ident.identity_commitment:
        raise IdentityError("identity_commitment_mismatch")
    for k in ident.as_dict():
        if k in FORBIDDEN_IDENTITY_FIELDS:
            raise IdentityError(f"forbidden_constitutional_field:{k}")


def identity_from_dict(d: dict[str, Any]) -> ConstitutionalIdentity:
    for k in d:
        if k in FORBIDDEN_IDENTITY_FIELDS:
            raise IdentityError(f"forbidden_constitutional_field:{k}")
    required = (
        "agent_id",
        "lineage_id",
        "birth_event_id",
        "schema_version",
        "created_at",
        "lifecycle_sequence",
        "identity_commitment",
    )
    for r in required:
        if r not in d:
            raise IdentityError(f"missing_field:{r}")
    ident = ConstitutionalIdentity(
        agent_id=str(d["agent_id"]),
        lineage_id=str(d["lineage_id"]),
        birth_event_id=str(d["birth_event_id"]),
        schema_version=str(d["schema_version"]),
        created_at=float(d["created_at"]),
        lifecycle_sequence=int(d["lifecycle_sequence"]),
        identity_commitment=str(d["identity_commitment"]),
    )
    verify_identity(ident)
    return ident
