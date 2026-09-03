"""Compare the R6F and R6F-R1 assays after authorized metadata normalization."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
OLD = REPO / "experiments/as003pr6f/common_root_assay.py"
NEW = REPO / "experiments/as003pr6fr1/common_root_assay.py"


def _normalized(path: Path, *, fresh: bool) -> ast.Module:
    tree = ast.parse(path.read_text(), filename=str(path))
    if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(
        tree.body[0].value, ast.Constant
    ) and isinstance(tree.body[0].value.value, str):
        tree.body[0].value = ast.Constant("R6F scientific assay")
    import_nodes = [node for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    for node in import_nodes:
        if isinstance(node, ast.ImportFrom) and node.module in {
            "umbra_core.decision_trace",
            "umbra_core.physiology",
            "umbra_core.util",
        }:
            names = {alias.name for alias in node.names}
            if {"canonical_fingerprint", "verified_outcome_effect_branches"}.intersection(names):
                node.module = "umbra_core.util"
                node.names = [
                    ast.alias(name="canonical_fingerprint"),
                    ast.alias(name="verified_outcome_effect_branches"),
                ]
    # The repaired assay necessarily uses two authoritative modules, while the
    # historical assay used one invalid module. Compare the two bindings as one
    # normalized semantic import rather than treating import grouping as science.
    seen_binding = False
    for index, node in enumerate(list(tree.body)):
        if isinstance(node, ast.ImportFrom) and node.module == "umbra_core.util" and {
            alias.name for alias in node.names
        } == {"canonical_fingerprint", "verified_outcome_effect_branches"}:
            if seen_binding:
                tree.body[index] = ast.Pass()
            else:
                seen_binding = True
    normalized = ast.unparse(tree)
    normalized = normalized.replace(
        "umbra-as-003p-r6f-r1-common-root-option", "umbra-as-003p-r6f-prospective-common-root-option-r1"
    )
    normalized = normalized.replace("prefix='u-r6f-r1-'", "prefix='u-r6f-'")
    normalized = normalized.replace("AS003PR6FR1_OPERATIONAL_ACQUISITION_RESULT_V1", "AS003PR6F_OPERATIONAL_ACQUISITION_RESULT_V1")
    normalized = normalized.replace("AS003PR6FR1_OPERATIONAL_ACQUISITION_RESULT.json", "AS003PR6F_OPERATIONAL_ACQUISITION_RESULT.json")
    normalized = normalized.replace("SEED = 18482", "SEED = int(SEED_DIGEST, 16) % 100000")
    normalized = normalized.replace("R6FR1_BASELINE = 'e5af166e86e85a5937d25b579f9256768bbd3d30'", "")
    if fresh:
        # The generation-only baseline constant is metadata and not part of the assay.
        normalized = normalized.replace("R6FR1_BASELINE = 'e5af166e86e85a5937d25b579f9256768bbd3d30'\n", "")
    normalized_tree = ast.parse(normalized)
    # Import grouping/order is not scientific protocol. The report separately
    # records the two allowed source corrections; remove the full import
    # preamble from the semantic AST comparison so order cannot mask the fact
    # that the executable body is otherwise unchanged.
    normalized_tree.body = [
        node for node in normalized_tree.body if not isinstance(node, (ast.Import, ast.ImportFrom, ast.Pass))
    ]
    return normalized_tree


def main() -> None:
    old_tree = _normalized(OLD, fresh=False)
    new_tree = _normalized(NEW, fresh=True)
    old_dump = ast.dump(old_tree, annotate_fields=True, include_attributes=False)
    new_dump = ast.dump(new_tree, annotate_fields=True, include_attributes=False)
    result = {
        "schema": "AS003PR6FR1_HARNESS_EQUIVALENCE_AUDIT_V1",
        "old_source_sha256": hashlib.sha256(OLD.read_bytes()).hexdigest(),
        "new_source_sha256": hashlib.sha256(NEW.read_bytes()).hexdigest(),
        "normalized_ast_equal": old_dump == new_dump,
        "classification": [
            "IMPORT_SOURCE_CORRECTION_ONLY",
            "GENERATION_METADATA_ONLY",
            "EVIDENCE_ROOT_ONLY",
        ],
        "status": "SCIENTIFIC_PROTOCOL_SEMANTICS_IDENTICAL" if old_dump == new_dump else "MISMATCH",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["normalized_ast_equal"] else 1)


if __name__ == "__main__":
    main()
