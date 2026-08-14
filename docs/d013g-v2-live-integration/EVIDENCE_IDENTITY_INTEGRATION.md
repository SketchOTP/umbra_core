# Evidence identity integration

Future runner identity, worker manifest, metrics, and run-result records carry the directive, formal execution ID, baseline commit, configuration fingerprint, verdict namespace, contract version, and V2 fingerprint.

The integration tests use a hypothetical D-013G future identity and verify that the legacy D-012B label does not leak into it.
