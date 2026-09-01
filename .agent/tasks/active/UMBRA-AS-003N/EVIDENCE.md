# AS-003N evidence protocol

Evidence JSON is written with file fsync, atomic rename, directory fsync, readback, and SHA-256 by `tools/as003n_evidence.py`. The helper imports no UMBRA module. Focused tests may import only the new pure substrate and standard-library fixtures; organism construction, runtime ticking, and Embodiment execution are excluded.

## Immutable pre-implementation locks

- Substrate contract: `ee3fec783c67365416ae68dce792cbebfa28ddd594127a4bf72509e91c7613bb`
- Branch-bound derivation: `31bc11e9914f1541228a25baa42d23034f573b903371b6f8aed833f5cc18b967`
- Evidence-composition contract: `4390ef6a7c576aff5aa681686ba4cc4f35e6b791134977d302c2121cd6de093a`
