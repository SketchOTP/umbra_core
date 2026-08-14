# Shadow contract specification

The contract is observational. It cannot mutate constitutional identity,
production governance, memory authority, relationship state, thresholds,
historical evidence, or verdicts.

| Boundary | Inputs | Outputs | Fail-closed rule |
|---|---|---|---|
| ExperimentDefinition | C0/S0, bounded budget, provenance | immutable definition fingerprint | reject wrong scope, authoritative seed, missing research markers |
| SeedManifest | seed 7, generator and purpose | seed fingerprint | reject mismatch or hidden authority |
| SubjectFactory | definition, disposable DB | production Organism | reject non-production source path |
| Scenario | S0 environment and no plant | HabitatState | reject canonical evidence path |
| Executor | Organism, HabitatEngine, tick budget | raw observations | reject incomplete budget or failed request mutation |
| MetricCollector | raw tick observations | declared metrics | reject synthetic or stale metric source |
| Aggregator | same execution ID raw rows | mean/count aggregate | reject mixed IDs, wrong evidence ID, or empty rows |
| Validator | hashes, IDs, budget, paths | accepted/rejected contract result | reject any mismatch |
| EvidenceWriter | non-authoritative results | CC-2 JSON only | never write `docs/evidence/d009/` |
| VerdictComputer | validation result | `PASS`/`FAIL_CLOSED` research interpretation | never emit `QUALIFIED` |
