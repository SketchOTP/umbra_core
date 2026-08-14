# Real perception equivalence

`tests/test_d013h_v2_formal_readiness.py` exercises the real worker
`run_diagnostic_ticks` path. Two genuine perception cycles produce different
observation IDs, timestamps, and noisy distance estimates while remaining in
the same action-relevant resource state.

Result: `material_evidence_changed == false` for ordinary stationary jitter.
A real environment repositioning through the harness perception path changes
the material key and is detected.

Classification: `NON_FORMAL_TEST`.
