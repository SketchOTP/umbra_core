# AS-003N evidence protocol

Evidence JSON is written with file fsync, atomic rename, directory fsync, readback, and SHA-256 by `tools/as003n_evidence.py`. The helper imports no UMBRA module. Focused tests may import only the new pure substrate and standard-library fixtures; organism construction, runtime ticking, and Embodiment execution are excluded.
