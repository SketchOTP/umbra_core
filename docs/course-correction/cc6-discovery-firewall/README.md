# UMBRA-CC-006 — Discovery / Qualification Firewall

Research-only contract validation. This dossier does not install ASAL, run an optimizer, access formal qualification data, or modify production authority. The deterministic harness uses three manually declared synthetic candidates and six explicit data zones.

Result: PASS — 26/26 required firewall faults rejected, zero silent failures; candidates remain `QUARANTINED`; formal qualification and protected scientific writes are unavailable.

## Scope boundary

Discovery may read sanitized research fixtures and write research-owned output/quarantine records only. No candidate can become `QUALIFIED`, `PRODUCTION`, or `AUTHORIZED`. A future operator directive, fresh freeze, fresh corpus, and separate formal validation are required.
