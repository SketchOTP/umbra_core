# AS-010 result — terminal closeout

Status: terminal. Verdict: `AS010_PROTOCOL_FAIL`.

Start baseline: `b5c7bb2b46e9355a8f5b658f25ebf4f1e7fea27b`.

AS-010 reproduced the AS-007 full configuration without modifying
`umbra_core/**`. The fresh formal population completed `32/32`: R0 `8/8`, R1
`8/8`, R2 `8/8`, and R3 `8/8`, each at `7200` ticks. The full-configuration
lifecycle passed at `500` ticks, including restart/Habitat restoration, true
physical body replacement, continuity, and compatible profile swap.

The post-lock boundedness run reached logical tick `100000` and observed
`521416` events, then failed during required final authoritative snapshot
collection with:

`umbra_core.embodiment.HabitatAuthorityError: habitat_engine_reattachment_required`

Source: `experiments/as010/downstream.py:104` →
`org.snapshot_if_due(force=True)` → `Embodiment.to_state()`.

This is a frozen post-lock harness protocol failure, not a boundedness pass or
scientific boundedness failure. No repair, retry, reseed, or rerun is allowed.
Real-time soak and causal ablation were not run. AS-008/AS-009 reduced-
configuration rows remain valid bounded evidence but are not combined into the
AS-010 full-stack result. Integrated viability remains **NOT QUALIFIED** and
CLOSE-03 remains blocked.

Counts: formal organisms `32`; lifecycle organisms `1`; boundedness organisms
`1`; control/shadow/diagnostic `0/0/0`; retries/reseeds `0/0`. Production delta
`0`; existing-test semantic delta `0`; successor started: `false`.

Evidence root:
`/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-010-full-configuration-integrated-qualification-r1/`.
