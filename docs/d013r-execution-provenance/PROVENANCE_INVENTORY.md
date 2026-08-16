# D-013Q capability provenance inventory

The D-013Q recovery trace contains 87 rows. There are 84 rows where
`selected_candidate` differs from `executed_capability`, but zero rows where
governance disagrees with execution and zero rows where execution disagrees
with the verified outcome.

| selected | executed | count | classification |
|---|---:|---:|---|
| MANIPULATE | IDLE | 76 | diagnostic capture/fallback (B) |
| MANIPULATE | REST | 1 | diagnostic capture/fallback (B) |
| MOVE | APPROACH | 4 | diagnostic capture/fallback (B) |
| MOVE | REST | 2 | diagnostic capture/fallback (B) |
| CHARGE | REST | 1 | diagnostic capture/fallback (B) |

The worker records the verified outcome capability as the executed capability,
then searches captured selections for a matching capability and falls back to
the first captured selection when no match exists. The mismatches therefore
belong to diagnostic capture/fallback provenance, not an authority-chain
disagreement. The evaluator now exposes `attempt_capability` explicitly while
retaining `selected_candidate` as diagnostic provenance.
