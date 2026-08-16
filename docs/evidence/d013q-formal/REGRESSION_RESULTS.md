# D-013Q regression closeout

Final isolated post-run results:

- D-013P-R1 focused: `11 passed`
- D-013P focused: `3 passed`
- D-013M focused: `4 passed`
- D-013A focused: `1 passed`
- D-013J runner regression: `5 passed`
- D-012 short-path process suite: `35 passed`
- D-009 evidence validator: `PASS` (`14` files, `3300` raw rows)
- D-010 evidence validator: `PASS` (`1900` raw rows)
- governance validator: `PASS` (ADOPTED; `19` required files and `10` Cursor rules)

One concurrent post-run attempt briefly produced `34 passed, 1 failed` in
D-012 because a disposable SQLite write returned `Errno 122: Disk quota
exceeded`. The exact disposable roots were cleaned, and the final isolated
short-path rerun passed `35 passed`. No source, evidence, threshold, or
governance contract change was made to address that environmental event.
