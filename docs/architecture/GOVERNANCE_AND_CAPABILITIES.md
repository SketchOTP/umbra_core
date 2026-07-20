# Governance and Capabilities

## Action chain (frozen)

```text
proposal
→ capability admission
→ policy
→ contract validation
→ runtime safety
→ execution
→ verified outcome
→ learning and memory
```

Evidence: Track 4 AEROS independent governance.

## Rules

- Low-risk habitat actions may be pre-authorized.
- Sensitive capabilities require stronger authorization.
- Unknown capability: **fail-closed** (UMBRA improvement over upstream default-ALLOW).
- Capability ≠ identity.
- Postconditions verified independently; no self-certify success.
- Learned competence never grants permissions.

## Motivation and goal arbitration (decisions #2, #9)

Combines:

- physiological urgency (vector H deficits)
- curiosity/novelty (bounded; Track 2 REFERENCE — allowed as secondary)
- learned preferences (from history)
- memory-derived expectations
- active commitments
- external requests (never auto-override safety)
- embodiment constraints

Must prevent: fixed need priority; one scalar happiness; compulsive interaction; goal thrashing; endless retries (Tracks 2, 6).

## Physiology interface (decisions #1, #3)

- **Viable ranges** over point setpoints for companion needs (Track 2 ADAPT).
- **Vector** motivation/state; reject scalar happiness as sole authority.
- Policies **read** H; never write H.
- Reflexes handle critical thresholds; learned systems do not replace them.

## Persistence justification

Embedded SQLite WAL event/state authority — see `STATE_AND_EVENT_MODEL.md`.
