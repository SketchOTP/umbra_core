"""D-011 bounded contracts; adapters submit derived observations only."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from umbra_core.util import canon_json, sha256_hex

MODALITIES = frozenset({"visual_features", "audio_features", "touch_contact", "spatial_context", "body_telemetry"})
_RAW_KEYS = frozenset({"raw", "raw_payload", "image", "video", "audio", "frame", "samples", "bytes", "base64", "location_trace"})


class PerceptionAdapterError(ValueError):
    pass


def _derived_only(value: Any, *, key: str = "") -> None:
    if key.lower() in _RAW_KEYS:
        raise PerceptionAdapterError("raw_payload_forbidden")
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            if not isinstance(child_key, str):
                raise PerceptionAdapterError("feature_key_not_string")
            _derived_only(child_value, key=child_key)
    elif isinstance(value, list):
        for item in value:
            _derived_only(item)
    elif not isinstance(value, (str, int, float, bool)) and value is not None:
        raise PerceptionAdapterError("feature_not_json_scalar")


@dataclass(frozen=True)
class AdapterManifest:
    adapter_id: str
    adapter_version: str
    modalities: tuple[str, ...]
    schemas: dict[str, str]
    max_payload_bytes: int = 4096
    raw_data_policy: str = "EPHEMERAL_ONLY"
    provenance_policy: str = "CHAIN_REQUIRED"
    compatibility: str = "D011-V1"

    def __post_init__(self) -> None:
        if not self.adapter_id or not self.adapter_version or not self.modalities:
            raise PerceptionAdapterError("manifest_identity_required")
        if set(self.modalities) - MODALITIES or set(self.modalities) != set(self.schemas):
            raise PerceptionAdapterError("manifest_modality_schema_mismatch")
        if self.max_payload_bytes < 1 or self.raw_data_policy != "EPHEMERAL_ONLY" or self.provenance_policy != "CHAIN_REQUIRED":
            raise PerceptionAdapterError("manifest_policy_invalid")

    def to_dict(self) -> dict[str, Any]:
        return {"adapter_id": self.adapter_id, "adapter_version": self.adapter_version, "modalities": list(self.modalities), "schemas": dict(sorted(self.schemas.items())), "max_payload_bytes": self.max_payload_bytes, "raw_data_policy": self.raw_data_policy, "provenance_policy": self.provenance_policy, "compatibility": self.compatibility}

    @property
    def manifest_hash(self) -> str:
        return sha256_hex(canon_json(self.to_dict()))


@dataclass(frozen=True)
class ObservationEnvelope:
    observation_id: str
    adapter_id: str
    source_id: str
    modality: str
    schema_version: str
    core_receipt_tick: int
    source_timestamp: str | None
    capture_interval: tuple[float, float] | None
    derived_features: dict[str, Any]
    confidence: float
    uncertainty: float
    provenance_chain: tuple[dict[str, str], ...]
    privacy_classification: str
    consent_state: str
    retention_class: str
    replay_class: str
    integrity_metadata: dict[str, str]
    manifest_hash: str

    def validate(self, manifest: AdapterManifest) -> None:
        if not self.observation_id or self.adapter_id != manifest.adapter_id or not self.source_id:
            raise PerceptionAdapterError("envelope_identity_invalid")
        if self.modality not in manifest.modalities or manifest.schemas.get(self.modality) != self.schema_version:
            raise PerceptionAdapterError("schema_or_modality_rejected")
        if self.core_receipt_tick < 0 or not 0.0 <= self.confidence <= 1.0 or not 0.0 <= self.uncertainty <= 1.0:
            raise PerceptionAdapterError("receipt_or_uncertainty_invalid")
        if not self.provenance_chain or self.manifest_hash != manifest.manifest_hash:
            raise PerceptionAdapterError("provenance_or_manifest_mismatch")
        if self.privacy_classification != "DERIVED_ONLY" or self.consent_state != "CONSENT_GRANTED" or self.retention_class != "DERIVED_BOUNDED" or self.replay_class != "AUTHORITATIVE":
            raise PerceptionAdapterError("privacy_or_replay_policy_rejected")
        _derived_only(self.derived_features)
        _derived_only(self.integrity_metadata)
        _derived_only(list(self.provenance_chain))
        if len(canon_json(self.derived_features)) > manifest.max_payload_bytes:
            raise PerceptionAdapterError("payload_bound_exceeded")

    def to_dict(self) -> dict[str, Any]:
        return {"observation_id": self.observation_id, "adapter_id": self.adapter_id, "source_id": self.source_id, "modality": self.modality, "schema_version": self.schema_version, "core_receipt_tick": self.core_receipt_tick, "source_timestamp": self.source_timestamp, "capture_interval": list(self.capture_interval) if self.capture_interval else None, "derived_features": self.derived_features, "confidence": self.confidence, "uncertainty": self.uncertainty, "provenance_chain": list(self.provenance_chain), "privacy_classification": self.privacy_classification, "consent_state": self.consent_state, "retention_class": self.retention_class, "replay_class": self.replay_class, "integrity_metadata": self.integrity_metadata, "manifest_hash": self.manifest_hash}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ObservationEnvelope":
        d = dict(data)
        d["capture_interval"] = tuple(d["capture_interval"]) if d.get("capture_interval") else None
        d["provenance_chain"] = tuple(d["provenance_chain"])
        return cls(**d)


@dataclass(frozen=True)
class SyntheticPerceptionAdapter:
    """Contract test fixture; it holds no organism reference or write capability."""

    manifest: AdapterManifest

    def submit(self, **kwargs: Any) -> ObservationEnvelope:
        kwargs.setdefault("adapter_id", self.manifest.adapter_id)
        kwargs.setdefault("manifest_hash", self.manifest.manifest_hash)
        envelope = ObservationEnvelope(**kwargs)
        envelope.validate(self.manifest)
        return envelope
