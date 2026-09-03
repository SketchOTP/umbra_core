# R6E scope and semantic lock

R6E is zero-organism research for a non-authoritative relation over a common root
set of already-known source-backed recovery options. It classifies each option as
`PRESERVED`, `DESTROYED`, or `UNKNOWN` after a candidate's supported immediate
effect branches. UNKNOWN is never treated as loss. The only strict relation is
known-option preservation: at least one option is preserved by A and destroyed by
B, with no converse loss or asymmetric UNKNOWN status.

The implementation is isolated under `experiments/as003pr6e/` and has no reader
in production, action selection, planning, or runtime. It does not modify the R6
`l2_precedes()` relation or any historical evidence.
