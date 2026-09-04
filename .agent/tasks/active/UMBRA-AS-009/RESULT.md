# AS-009 result

Status: terminal: `AS009_PROTOCOL_FAIL`. The exact starting baseline is
`f5e73ec4a3f5b677590d079d2bf2e506a699134e`.

AS-008 is preserved as terminal `AS008_PROTOCOL_FAIL`. Fresh formal R2/R3
populations completed `8/8` each at `7200` ticks. The R2 repair is limited to
constructing the preregistered partner as a HabitatEngine `SOCIAL_ENTITY` and
using HabitatEngine visibility commits for occlusion/reappearance.

The first downstream lifecycle attempt created one organism, loaded it twice,
and executed `400` ticks, then failed because the downstream harness did not
reattach HabitatEngine after reload before invoking body replacement. The
failure is terminal protocol evidence under the no-repair/no-retry boundary.
No downstream boundedness, soak, or ablation gate ran; production and existing
test semantic deltas are `0/0`; retries/reseeds are `0/0`. Evidence manifest:
`/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-009-r2-r3-habitat-authority-integrated-qualification-r1/AS009_EVIDENCE_MANIFEST.json`.
