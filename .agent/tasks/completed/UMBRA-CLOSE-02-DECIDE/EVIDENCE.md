# UMBRA-CLOSE-02-DECIDE evidence ledger

Evidence is written only to the isolated Atlas root:

/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-close-02-decide-r0-attribution-r1/

Required artifacts:

- CLOSE02_DECIDE_AB_SOURCE_MAP.json
- CLOSE02_DECIDE_CONFIG_MANIFEST.json
- CLOSE02_DECIDE_TRACE_PARITY.json
- CLOSE02_DECIDE_A_TRACE.jsonl
- CLOSE02_DECIDE_B_TRACE.jsonl
- CLOSE02_DECIDE_ALIGNMENT.json
- CLOSE02_DECIDE_VERDICT.json
- CLOSE02_DECIDE_VALIDATION.json
- EVIDENCE_HASHES.json

Terminal note: the external collector stopped control A at trace tick 3869
before natural failure or the 7200-tick horizon. The partial trace is retained
as CLOSE02_DECIDE_A_TRACE_PARTIAL.jsonl. Candidate B was not run.

The A/B runs are each single invocations with seed 45878900. Raw traces and
their manifests are immutable after terminal closeout.
