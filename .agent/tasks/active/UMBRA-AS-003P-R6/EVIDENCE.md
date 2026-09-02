# AS-003P-R6 evidence protocol

Evidence root:
`/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-003p-r6-l2-schedulability-attribution-r1/`.

R5A artifacts are immutable read-only inputs. R6 artifacts use create-once atomic
publication, file fsync, atomic rename, directory fsync, SHA-256 readback, and a
final manifest. The research implementation may parse retained JSON/JSONL and run
pure synthetic fixtures only; it must not import or execute organism runtime.

Starting source hashes:

- R5A final manifest: `271a717821c07defbc0b5b89191065f0e5923e60bbd71dac0855fd45ecebb805`
- SHADOW planning trace: `58ea3a6e8fbb81443f4e569a811b0ded2e3b273fd4221ed497923965a56903e8`
- SHADOW decision trace: `4c48d1db24e4600a3f5e1c855efec9b1eec1937f8ca1409c52070fc6cbbdd380`

Published artifact hashes:

- state reconciliation: `d7dcd541b2cf4e7a839b4c12f2a2fd2e36c49aa3a53a5deefd2970bf39dec030`
- source trace attestation: `525621b83310c322e3fef9c14d99429b8ebd3f3dc1224db8e6cb65427f0af8fb`
- hypothesis lock: `8b3b4233d702279bcf3b740a5bec0845ffaec4e1a3e7b4d316e5e95db95e1d81`
- AS-003L contract recovery: `0188d0efe98674bc7289cc387d91648cdbf67a3bde02bac92f4cf0789560fcab`
- substrate gap matrix: `5d4b7d0ed9cef761278ee8848bf99c8b20928217945ab3e3e84b4782bcd99de1`
- external prior art: `307b16750045dbedf1968794ee04f902b1fc0aa3c91dfdfd9b8811c9e6423a03`
- L2 contract lock: `9d0d92e620c034223c108f239bf5c6bf403c716847700a62ce0d208a1b02455a`
- pure tests: `741b1b192a13c9d96dc823d76f17dd65cca697dc4404df48e6567f77e5f1be00`
- profile information loss: `549dad2fe7c8988d230c08db4805470dfd8bf2d7cc9f913032daebb222cdac66`
- temporal envelope audit: `a30b3ce2dd974dfea48f9b7080ab67f59ca2b18cf277dc6553ecfa4c28043449`
- retained L2 application: `bacfd4e449353bfac91c07607b8c8a480d829c32a8afd537e0fb5a6f785ffa61`
- causal attribution: `467b6f4684b6294b2319d775ceedabe290f93e1a0ad5de9568bfb4ebe5b8d63b`
- terminal verdict: `5b7e8d14acaa23ccec7485d40ca20c4c4ca06793b4c1559fe06b8fd37bc797fa`

- final evidence manifest (13 inventoried artifacts):
  `37bfe447aa552bef7fba7b608b684ff6c5b2e6acbb784d78009605cc49bd306a`

Manifest readback and every inventoried artifact hash: PASS. R5A planning and
decision trace hashes remained unchanged after analysis.
