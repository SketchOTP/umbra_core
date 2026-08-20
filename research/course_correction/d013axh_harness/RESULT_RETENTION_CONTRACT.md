# Result retention contract

The SQLite ledger and immutable result/confirmation payloads are authoritative
harness evidence. Scratch files are recomputable and may be removed only after
the durable result is published and ledger-complete. The failed AX and AXR
trees are outside this contract and are never cleaned by AXH.
