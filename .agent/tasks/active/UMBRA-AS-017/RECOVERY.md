# AS-017 crash recovery candidate

This reconstruction begins from committed baseline `fd8c50e1134d7d2ef54e20148ac9b7880e63708d` after the uncommitted earlier AS-017 worktree was lost in a host crash.

V1 is a zero-tick GVFS SQLite infrastructure failure. V2 contains two historical R0 development observations only; their source fingerprint is unavailable and they are not combined with this candidate.

The reconstructed candidate is committed and pushed before development execution. Its development runner requires the exact checked-out candidate commit, a create-once local SQLite runtime directory, a create-once remote evidence directory, and the registered manifest hash in every case result.

## V3 result and evidence boundary

V3 at `f6f9a2b8967cd40a8e0dcdc68619b9ee536961cb` completed all 16 registered cases at 7,200 ticks. Isolated copies of every exported database matched its case hash, passed SQLite integrity, contained an identity, checkpoint, snapshot, retained temporal-chain event, and terminal snapshot/temporal tick 7,200. The durable validation artifact is `AS017_V3_DURABLE_CASE_VALIDATION.json`, SHA-256 `df6013e92de5840d034e0c78d769249480a6c639bd5a1051ed8d459c6d91d353`.

The V3 persistence schema does not retain an exact certificate-witness-to-verified-outcome linkage. Consequently the 16/16 result is bounded development survival evidence; certificate-to-execution validation remains pending and no scientific lock is ready.

## V4C certificate-linkage development failure

V4C at `aab480561736d8baaebe041c01a3d938bcc15a47` is preserved as a separate
development attempt. Its first R0 case (`54869811`) stopped at tick 206 with
`NO_SAFE_ACTION` and crossed the energy critical boundary at tick 207; no
subsequent cases launched. The durable result SHA-256 is
`df08a67712f9a730c28d5f741760203087ceb12362825cf7bf827522f1227009`.

Its trace established a source-level selection defect, not a completed causal
explanation of every prior failure: a current effect-derived CHARGE regulator
could be present while an uncertified MAY approach was selected through the
disconnected legacy root-wide direct-path status. The repair removes that
selection authority. A current action that effect-corrects every active
physiological dimension is selected ahead of an uncertified MAY route, without
claiming a future continuation certificate; where no such vector regulator
exists, the MAY route remains lawful and selectable.

V4C also proved that the trace format must distinguish a Governance proposal
ID, an adapter execution ID where present, and a verifier outcome ID. Future
linkage reductions retain those separate identities. V4C is not combined with
V3 and cannot qualify the changed candidate.
