# Root-Cause Adjudication

Verdict: `D013A_CAUSAL_DEFECT_CONFIRMED_NO_REMEDIATION` was not selected because a narrowly scoped correction was authorized by the D-013A gate after reproduction. Final diagnostic verdict: `D013A_CAUSAL_CORRECTION_DIAGNOSTIC_PASS`.

The exact source defect is confirmed in `umbra_core/arbitration.py`: stale non-energy focus was retained whenever energy was in the recovery pool but had not yet crossed the critical bound. The B2 trace, bounded real-path reproduction, and focused red test agree on the mechanism.
