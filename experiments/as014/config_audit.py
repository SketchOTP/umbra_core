"""Programmatic AS-014 full-configuration and persistence-seam audit."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from experiments.as010.full_config import as010_config, semantic_fingerprint
from experiments.as014.full_config import BASELINE, DIRECTIVE, LEDGER_CONTRACT, config, fingerprint
from tools.as014_evidence import publish


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="as014-config-audit-") as temporary:
        root = Path(temporary)
        old = as010_config(41414011, root / "as010.sqlite", "R1", bounded=True, route_learning=True)
        new = config(41414011, root / "as014.sqlite", "R1")
        old_semantic = semantic_fingerprint(old)
        new_semantic = semantic_fingerprint(new)
        new_without_ledger = dict(new_semantic)
        new_without_ledger.pop("ledger", None)
        differences = {
            key: {"as010": old_semantic.get(key), "as014": new_without_ledger.get(key)}
            for key in sorted(set(old_semantic) | set(new_without_ledger))
            if old_semantic.get(key) != new_without_ledger.get(key)
        }
        result = {
            "schema": "AS014_FULL_CONFIGURATION_CONTRACT_V1",
            "directive": DIRECTIVE,
            "baseline": BASELINE,
            "as007_equivalent_source": "experiments/as010/full_config.py",
            "full_stack_flags": {
                "bounded_continuation_enabled": new.bounded_continuation_enabled,
                "world_model_enabled": new.world_model_enabled,
                "route_demand_learning_enabled": new.world_model_config.route_demand_learning_enabled if new.world_model_config else None,
            },
            "preexisting_semantic_differences": differences,
            "ledger_only_addition": fingerprint(new)["ledger"],
            "verdict": "AS007_FULL_CONFIGURATION_REPRODUCED_WITH_AS014_PERSISTENCE_SEAM"
            if not differences and fingerprint(new)["ledger"] == LEDGER_CONTRACT
            else "SEMANTIC_MISMATCH",
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    publish("AS014_FULL_CONFIGURATION_CONTRACT.json", result)


if __name__ == "__main__":
    main()
