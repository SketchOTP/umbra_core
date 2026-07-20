# Upstream reproduction

## Environment

```bash
python3 -m venv /tmp/aeros-core-venv
/tmp/aeros-core-venv/bin/pip install -e '.[dev]'
# later: pip install jsonschema numpy  # needed by some modules/tests
```

Pin: `3e46d82bf5cd829df8d00061b865b7eb709e278d` / aeros 0.15.0

## Results

| Check | Result |
|---|---|
| Install | PASS |
| CLI `aeros --help` | PASS |
| Governance/policy/contracts/evolution pytest | **371 passed** |
| Runtime tests (excl. dreamer needing extras) | **271 passed** |
| audit+ecm | 276 passed, **2 failed** (sandbox/seccomp), 10 skipped |
| Lint/type | not claimed |
| MuJoCo/hardware | not enabled |
| Bridge identity integration | blocked initially on `jsonschema` |

## Governance path evidence

Upstream `RuntimeGateway.execute_with_policy` denies before execution; allow path records audit. Covered by `tests/governance/test_policy.py`.

## Modifications

None to upstream source. Extra deps installed only in ephemeral venv.
