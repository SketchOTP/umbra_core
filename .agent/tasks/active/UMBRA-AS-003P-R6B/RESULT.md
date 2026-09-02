# R6B result

Terminal verdict: `AS003PR6B_IMPLEMENTATION_FAIL`.

Exact starting baseline: `3604fa6a4a4e01c764913af55474e7ad9495325f`.
Governance start: `d3ad4ea8f98c7e8fb24d654d10a6f2f4c871cafb`.
Contract lock: `b951ac8` (SHA-256 `9f81daf9abad7512a244dedce4e33bee1fd8914b3158727fa845745b0578545a`).
Implementation: `0d850ee`.
Assay harness/audit: `0a1ca4f0892084f66f5ee9a38023b81654342c65`.

The default-off, WorldModel-owned `VerifiedRouteExperience` primitive passed
`25/25` focused tests twice. The frozen bounded operational command executed
one nominal and one failure leg (`2` organisms, `14` ticks, retries/reseeds
`0/0`). The failure leg retained exact opportunity/body binding and verified
`movement_slip`. The nominal leg did not satisfy Q1's required continuous
`APPROACH ... APPROACH -> CHARGE` episode: an intervening emitted `ORIENT`
invalidated the active route episode, and the later `CHARGE` created only a
zero-movement terminal sample. No qualification claim is made.

The focused protected suite was `87 passed / 1 inherited baseline nonpass`;
the nonpass is the pre-existing AS-003N firewall test, confirmed by exact
baseline source inspection. Production changes are confined to the authorized
R6B route seam; there is no planning or action-selection reader. No retry,
reseed, long-horizon run, AS-004, CLOSE-03, or successor is authorized.

Evidence root:
`/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003p-r6b-verified-route-learning-r1/`.
