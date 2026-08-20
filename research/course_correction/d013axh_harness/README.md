# D-013AXH synthetic durable harness

This package is a research-only, synthetic/non-scientific qualification
harness for D-013AXH. It does not import `umbra_core`, does not load AX target
configuration, and cannot issue an AX scientific verdict.

The implementation uses only Python standard-library `sqlite3`, atomic result
publication with `os.replace`, deterministic SHA-256 identity, bounded
`ThreadPoolExecutor` workers, and restartable ledger transitions.
