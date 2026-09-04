# AS-007 result

Status: TERMINAL — downstream protocol failure after positive frozen A/B/R1 gate.

Exact baseline: `22c96dd711126d0e87f637032a7871308fede803`.

The permanent AS-006 result remains `AS006_KNOWN_R1_FAIL`; its retained
evidence is historical and is not being rewritten or rerun.

The retained R1/S16 benchmark is coherent: the reversal changes the
policy-visible recovery situation, and the retained trace includes successful
post-reversal fatigue-reducing actions. The terminal `REST`/`not_at_rest`
sequence is therefore attributed to missing current terminal-readiness
adjudication, not an impossible benchmark. Coherence audit:
`AS007_R1_COHERENCE_AUDIT.json`, SHA-256
`20422aaee9c6c07c12fa281c51c16a26d9b9107555a79b48b7201f353e98dd72`.

The implementation contract is now locked as a categorical, source-backed
current-readiness gate for `REST`, `CHARGE`, and `INSPECT`. Adapter admission
and the existing Embodiment preflight are the authority chain; only
`EXECUTABLE`, `NOT_EXECUTABLE`, or `UNKNOWN` crosses into arbitration. Motion
remains execution-verified, and planning/route evidence remains unread.

Pre-freeze validation is positive. Focused protected tests passed `47/47`
twice. The non-scientific R1/S16 development gate completed `240/240` ticks;
it recorded `255` categorical terminal-readiness evaluations, `41` post-
reversal non-executable terminal evaluations, zero critical failure, and zero
unavailable terminal selections. A separate common-root observer-only gate
completed one control and one shadow branch at `500/500` ticks with zero
semantic differences and zero RNG divergence. These gates grant no planning
or integrated-viability authority.

The dedicated frozen scientific sequence then completed exactly once:
Diagnostic A (`R0`, seed `45878900`, `500/500`), Diagnostic B (`R0`, seed
`22023239`, `3500/3500`), and Known R1 (`S16`, seed `57531938`, `7200/7200`).
All completed without critical failure; organism runs/ticks were `3/11200`,
retries/reseeds `0/0`, and no downstream population started before the gate.
Result artifact SHA-256:
`8f807c227d182bc782eb9f7403b85b9c46c07913c46506cbc090ac53d353c83b`.

After R1 passed, the existing D-014 formal preflight was invoked for the
authorized fresh R0–R3 population gate. Its smoke preflight passed technically,
but selected R1 seed `57531938`, the explicitly prohibited known R1 seed. This
is retained as a protocol failure, not qualification evidence:
`AS007_PROTOCOL_FAILURE.json`, SHA-256
`56c0d8b97ad98ecf202e8967c1f539ea595cc130c8350a71857ac0e7aa0f4fd2`.
The preflight created four smoke organisms and advanced 80 ticks; no 32-run
matrix, lifecycle, accelerated, real-time soak, or ablation phase began.
Terminal verdict: `AS007_PROTOCOL_FAIL`. AS-007 integrated viability remains
unqualified and no successor started.
