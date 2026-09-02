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
