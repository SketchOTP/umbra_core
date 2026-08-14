# V2 evidence publication

V2 publication now requires both final artifacts:

- `P0_RECOVERY_EVALUATION_TRACE.jsonl`
- `P0_READONLY_POSTRUN_VALIDATION.json`

The copy path fails closed if either source is missing. When formal identity
is supplied, both artifacts are checked for directive, execution ID, starting
commit, configuration fingerprint, contract version, and contract fingerprint.

V1 publication does not require either V2-only artifact.
