# Regression results

- D-013C focused rollback regression: PASS
- ordinary SIGTERM identity recovery: PASS
- force-kill identity recovery: PASS
- dead-worker reclaim false/true: PASS
- complete `tests/test_d012_process_boundary.py`: 27 passed
- D-013A focused regression: 1 passed
- D-009 validator: PASS, 14 files, 3300 raw rows
- D-010 validator: PASS, 1900 raw rows, zero errors
- governance validator: PASS
- full suite: 693 passed, 2 skipped, 1 failed at the pre-existing D-010 runtime-tick inventory test
