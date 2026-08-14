# CC-6R2 Operator Review Findings

This document preserves the operator findings against CC-6R. The remediation
is research-only and does not amend CC-6 or CC-6R.

1. Provenance was not independently recomputed for source, sanitized input, schema, and partition links.
2. Symlink fixtures did not originate beneath permitted roots.
3. Traversal was not a separate mutation.
4. A-Z meanings were not preserved.
5. AA-AM were incomplete.
6. Several original firewall checks disappeared.
7. Machine-readable evidence omitted fields claimed by the matrix.
8. Some tests manually raised expected detectors instead of exercising contract invariants.

CC-6R2 addresses each finding with frozen internally computed provenance,
canonical A-AM records plus AN-AQ independent provenance faults, real
in-root symlink fixtures, complete records, and a mechanical consistency
validator.
