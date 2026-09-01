# UMBRA-AS-003P-R3

## Authority

Prospective observer-parity qualification from exact baseline
`237251fd9e6b859284d45fe6da42a54a5e0d05a3` after Architect acceptance of
`AS003PR2_COMPARATOR_FALSE_POSITIVE_CONFIRMED`.

## Objective

Implement, adversarially qualify, and freeze an owner/source-semantic parity
comparator before any organism execution, then use it for exactly one fresh
matched control/shadow pair. Interpret only fresh R3 modal evidence and only
after prospective semantic parity passes.

## Scope locks

- AS-003P, R1, and R2 evidence and verdicts remain immutable.
- All AS-003P scientific implementation and runtime shadow-hook code remains
  byte-identical throughout R3.
- Fixture is fixed to CLOSE-02R/AS-003C Diagnostic A, R0/S0, seed `45878900`,
  horizon `500`.
- Exactly one control and one shadow execution are authorized after lock;
  retries and reseeds are zero.
- Production, modal semantics, action selection, AS-002, AS-004, and CLOSE-03
  changes are prohibited.
- R1 raw modal counts are invalid and cannot inform R3 criteria.

## Terminal boundary

Return exactly one permitted AS-003P-R3 verdict. Do not start a successor.
