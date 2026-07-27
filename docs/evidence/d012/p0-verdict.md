# UMBRA-D-012B formal P0 verdict

```text
UMBRA_D012B_P0_INTEGRITY_FAIL
```

- Formal execution: `d012-p0-6de0bb3-20260727T1424Z`
- Starting commit: `6de0bb3`
- First failing invariant: `invalid_physiological_state`
- Stop: 100.061 active seconds; no extension
- Authoritative cleanup snapshot: tick 191, energy 0.0015, critical lower bound 0.05
- Identity: preserved
- Event chain: valid through sequence 766
- Durable raw sensor payloads: zero
- Process cleanup: PASS
- Frozen D-010 regression fingerprint: unchanged

Gate disposition:

- Gate 0 entry integrity: PASS
- Gate 1 process separation: PASS
- Gate 2 database ownership: PASS
- Gate 3 autonomous operation: FAIL — autonomous ticking continued, but physiology became critical
- Gates 4–7 perception/restart/checkpoint/resource stability: NOT REACHED
- Gate 8 privacy: PASS through stop
- Gate 9 regression integrity: PASS after an honestly recorded disk-quota-invalidated first attempt
- Gate 10 clean closeout: PASS

P1 and P2 were not launched. D-012 remains active and unqualified. This P0 failure does not authorize D-012C or any longer campaign.
