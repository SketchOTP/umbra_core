# UMBRA-AS-001 result

## Verdict

`AS001_CURRENT_ARBITRATION_REPLACEMENT_REQUIRED`

## Evidence-grounded finding

UMBRA's existing SelfModel and WorldModel contain enough learned state to construct bounded, one-step, candidate-relative preselection consequence views after their deterministic calculations are separated from pending/history mutation. Missing predictions remain `UNKNOWN`; views do not rank, execute, learn, or persist as facts. Only the selected candidate receives a committed prediction and can later learn from `VerifiedOutcome`.

The current ordinary scalar scorer cannot consume those views defensibly. It directly sums heterogeneous authored and learned-influenced components without established common units or calibration. Adding consequence evidence to that sum would preserve the defect and duplicate capability-name assumptions.

## Smallest supported replacement boundary

Replace only ordinary `Arbitrator.score_candidate` scalar-total evaluation and its additive modifier interface with bounded evidence-conditioned distributed competition. Preserve candidate generation, hard safety and recoverability admissibility, CLOSE-02T one-final-action authority, CLOSE-02Z candidate-stable stochastic identity, Governance, Embodiment, VerifiedOutcome, and selected-only learning.

## Integrity

- Production changes: 0
- Organism runs: 0
- Retries: 0
- Reseeds: 0
- Focused zero-run proofs: 8/8 PASS
- Authority 3.0: PASS
- Governance: PASS
- Evidence manifest: 14/14 PASS
- Manifest SHA-256: `8681c83d0eff272b27518164bf2d24bff7bebfd80d3bc6811ca18c5374f34ef5`

No AS-002 or implementation successor is authorized. Return to Architect for a separately authorized replacement contract/implementation decision.
