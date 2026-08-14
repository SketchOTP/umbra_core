# CC-6R fault coverage matrix

| Requirement | Implementation | Positive | Negative | Detector |
|---|---|---|---|---|
| Candidate configuration fingerprint | `Firewall.score` | valid manifest | O, P | candidate configuration fingerprint validator |
| Candidate provenance fingerprint | `Firewall.score` | matching chain | Q | provenance candidate fingerprint validator |
| Partition fingerprint | `Firewall.score` | matching manifest | R, S | partition/provenance partition validators |
| Quarantine immutability | `Firewall.finalize/get_record` | final ranked record | T, V, W | quarantine immutability validator |
| Resolved protected paths | `Firewall.write_policy` | research output root | C–F, Y, AA | resolved write path validator |
| Read/write symlink isolation | `_safe_read/write_policy` | safe fixture | Y, Z | path/embargo validators |
| Embargo enumeration boundary | `DiscoveryView` | discovery IDs | AB | embargo enumeration validator |
| Partition disjointness | `validate_partitions` | disjoint sets | AC | partition overlap validator |
| Lifecycle | `freeze/start/close` | DRAFT→FROZEN→RUNNING→CLOSED | K–M, AD–AF | lifecycle validators |

All 32 fault records have explicit IDs, mutations, expected/actual detectors, and rejection status in `fault-injection-results.json`.
