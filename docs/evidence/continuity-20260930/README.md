# Baseline/life/companion review — PARTIAL

The original AS-018 P0 V2 aggregate stdout survives, but its detailed
32-case artifacts were not recovered. `P0_RETROSPECTIVE_AUDIT_FINAL.json` is BLOCKED,
not a replacement formal result. No historical organism was resumed/rerun.

`BASELINE_LIFE_COMPANION_REVIEW_SEALED.json` binds the surviving job, artifact
inventory, source hashes, environment, probe attempts, targeted test outputs
and explicit limitations. The accepted production subtree remains unchanged.

`life-result.json` and `life-segment-*.json` are shortened DEVELOPMENT
continuity evidence; the original SQLite/sidecars, trace and journal live in
the inventory's retained local work directory and separate durable export.
The archived probe source bytes match its recorded execution hash; the later
CLI seed guard and failure-counting improvements are not falsely attributed
to that earlier 1024-tick run. The active harness is covered by the final
targeted tests. JUnit XML records actual executions, not collection.

The protocol in `docs/qualification/BASELINE_LIFE_COMPANION_PROTOCOL_V1.md`
is prospective, CANDIDATE — NOT CANONICAL. No P1–P5, 100k/S3, human companion
sessions, or qualified reusable-core release was performed.

Literal retrospective audit (never instantiates an organism):

```bash
python tools/umbra_baseline_audit.py \
  --result /path/to/ORIGINAL-result.json \
  --journal /path/to/ORIGINAL.stages.jsonl \
  --work /path/to/ORIGINAL-work \
  --output /path/to/NEW-audit.json
```

Use only quiescent original evidence, preserve any matching WAL/SHM, and write
a fresh report. Missing evidence exits 2/BLOCKED; tampering exits 1/FAIL.
PASS means the implemented copy-only checks passed, never matching stdout
alone. It does not independently prove numerical predictions or complete
trace-to-committed-outcome correspondence. Those acceptance claims remain
separately gated on retained authority evidence and review.

The initial audit/report remain immutable predecessors. The archived
`baseline-audit-initial-source.py` matches that initial report's validator
fingerprint; the final report binds the bounded journal/metadata reader and
all seven actual JUnit runs (overlapping selections, not additive test counts).
`HANDOFF.md` is the consolidated scope/acceptance report.
