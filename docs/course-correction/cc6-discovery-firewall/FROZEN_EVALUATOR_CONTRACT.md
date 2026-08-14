# Frozen evaluator

Before scoring, the evaluator freezes feature definitions, metric versions, normalization, ranking/ties, missing-data behavior, partition manifest, and input/output schemas into one fingerprint. Any mutation after freeze invalidates/rejects the run. CC-6 fingerprint: `9cb08895466af3f8ae81fa2d4340d5aa743eab599750f275c2ee5486646c2326`.
