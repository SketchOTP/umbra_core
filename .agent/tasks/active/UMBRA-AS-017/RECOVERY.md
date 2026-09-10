# AS-017 crash recovery candidate

This reconstruction begins from committed baseline `fd8c50e1134d7d2ef54e20148ac9b7880e63708d` after the uncommitted earlier AS-017 worktree was lost in a host crash.

V1 is a zero-tick GVFS SQLite infrastructure failure. V2 contains two historical R0 development observations only; their source fingerprint is unavailable and they are not combined with this candidate.

The reconstructed candidate is committed and pushed before development execution. Its development runner requires the exact checked-out candidate commit, a create-once local SQLite runtime directory, a create-once remote evidence directory, and the registered manifest hash in every case result.
