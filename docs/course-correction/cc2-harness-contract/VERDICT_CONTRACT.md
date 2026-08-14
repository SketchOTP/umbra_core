# Verdict contract

`raw execution → metric → aggregate → validation → research interpretation`.

The shadow harness emits only `PASS` when the declared research contract passes,
or `FAIL_CLOSED` when a comparison or fault test fails. It refuses missing raw
execution, wrong execution IDs, seed mismatch, incomplete budget, metric-source
substitution, invalid aggregation, contaminated evidence paths, and
verdict/evidence mismatch. It cannot emit `QUALIFIED`, rewrite evidence, or
change historical verdict logic.
