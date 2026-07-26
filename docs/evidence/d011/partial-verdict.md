# D-011 partial verdict

Verdict: `UMBRA_D011_PARTIAL`.

Implemented and verified: synthetic submit-only manifests/envelopes; derived-only payload rejection; schema and manifest mismatch rejection; provenance/privacy/replay metadata checks; confidence and uncertainty preservation; bounded duplicate suppression; authoritative accepted-observation events; snapshot/restart restoration; two synthetic adapters; and a 100,000-observation bounded stress run.

The qualification gates are not all evidenced yet. In particular, the full preregistered C0–C8 ablation matrix, adaptive real-time stability protocol, formal replay-from-ledger reconstruction, independent review, and final evidence-hash bundle have not been run. D-011 is therefore not qualified, and D-012 is not authorized by this result.

Executed checks:

- `pytest -q tests/test_d011.py` — 4 passed.
- `pytest -q tests/test_d001.py` — 33 passed.
- `pytest -q tests/test_d009.py` — 108 passed.
- `python experiments/d011/run_experiment.py --count 100000` — 100,000 submissions; 256 stored observations; 512 deduplication IDs; 15.04 s; +0.41 MiB RSS.
- `pytest -q` and `python tools/validate_governance.py` — succeeded in the final regression command.
