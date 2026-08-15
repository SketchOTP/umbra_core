# D-013J Regression Results

## Passed focused validation

- `tests/test_d013j_runner_entrypoint.py`: **5 passed**
- D-013J focused governance/regression matrix: **88 passed**
- governance validator: **PASS**
- governance tests: **5 passed**
- D-009 validator: **OK**
- D-010 validator: **PASS**
- D-013I evidence/configuration preservation checks: **PASS**

The focused matrix covered the D-013J runner tests, D-013A, D-013F,
D-013G, D-013H, D-013H-R1, D-012 process/supervision checks, D-009/D-010
governance, and the repository governance tests.

## Repository-wide suite

The first repository-wide run was invalid as an environment result because
the Atlas `/tmp` 16 GiB tmpfs reached its capacity boundary and produced
widespread SQLite `disk I/O error` failures.

A second run redirected pytest temporary files to the secondary volume and
completed with:

`725 passed, 16 failed, 2 skipped, 2 warnings`

The 16 failures were confined to the existing D-010 runtime-tick inventory
assertion and D-012 worker/process-boundary startup tests. The D-012 failures
were reproduced in isolation and reported `Errno 122: Disk quota exceeded`
during ordinary manifest/SQLite writes. No D-013J test failed in the focused
validation, and no formal worker or formal P0 was launched.

The pre-existing D-010 result remains authoritative:
`UMBRA_D010_PERFORMANCE_FAIL`.

## Formal-run boundary

- D-013I formal evidence was hash-preserved.
- No D-013J formal tag was created.
- No formal P0 execution, retry, restart, or scientific evidence generation
  occurred.
