# V1/V2 runner boundary

V1 behavior remains unchanged: `charge_selected_but_not_executable` remains
the V1 terminal code.

Under V2, an unexpected legacy terminal code now produces the fail-closed
`V2_CONTRACT_PATH_INCONSISTENCY` result. It is no longer silently suppressed
as a safe denial.
