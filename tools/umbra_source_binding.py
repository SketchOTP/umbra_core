"""Prospective source binding; cannot reconstruct lost historical provenance."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sqlite3
import subprocess
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.as017_evidence import publish_json_once, stream_sha256

ROOT = Path(__file__).resolve().parents[1]


def verify_accepted_production(subject: str, root: Path = ROOT) -> None:
    root = root.resolve()
    listing = subprocess.check_output(
        ["git", "ls-tree", "-r", "-z", subject, "--", "umbra_core"], cwd=root)
    expected_python = set()
    for entry in listing.split(b"\0"):
        if not entry:
            continue
        metadata, raw_name = entry.split(b"\t", 1)
        mode, kind, digest = metadata.decode().split()
        name = raw_name.decode()
        path = root / name
        if mode not in {"100644", "100755"} or kind != "blob" or path.is_symlink():
            raise ValueError(f"unsupported_production_file:{name}")
        calculated = hashlib.sha1(f"blob {path.stat().st_size}\0".encode())
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                calculated.update(chunk)
        if calculated.hexdigest() != digest:
            raise ValueError(f"accepted_production_file_mismatch:{name}")
        if name.endswith(".py"):
            expected_python.add(name)
    actual_python = {p.relative_to(root).as_posix() for p in (root / "umbra_core").rglob("*.py")}
    if actual_python != expected_python:
        raise ValueError("unregistered_or_missing_production_python")


def capture_source_binding(root: Path = ROOT) -> dict:
    root = root.resolve()
    # Include untracked runtime Python too. A new module cannot quietly evade a
    # git-tree-only fingerprint. Runtime contracts are included separately.
    paths = set()
    for directory in ("umbra_core", "experiments", "tools"):
        for path in (root / directory).rglob("*.py"):
            if not path.is_file() or not path.resolve().is_relative_to(root):
                raise ValueError(f"source_outside_checkout:{path}")
            paths.add(path.relative_to(root).as_posix())
    for name in ("experiments/as018/AS018_SCIENTIFIC_LOCK_CONTRACT_V2.json",
                 "experiments/as018/AS018_FORMAL_SEED_MANIFEST_V2.json"):
        if (root / name).is_file():
            paths.add(name)
    for name in ("requirements.txt", "requirements-dev.txt", "pyproject.toml", "uv.lock", "poetry.lock"):
        if (root / name).is_file():
            paths.add(name)
    origins = {}
    for name, module in tuple(sys.modules.items()):
        if not name.startswith(("umbra_core.", "experiments.", "tools.")):
            continue
        location = getattr(module, "__file__", None)
        if location:
            path = Path(location).resolve()
            if not path.is_relative_to(root):
                raise ValueError(f"import_outside_checkout:{name}:{path}")
            origins[name] = path.relative_to(root).as_posix()
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    production_tree = subprocess.check_output(["git", "rev-parse", "HEAD:umbra_core"], cwd=root, text=True).strip()
    return {"schema": "UMBRA_PROSPECTIVE_SOURCE_BINDING_V1", "head": commit,
            "production_git_tree": production_tree,
            "files": {name: stream_sha256(root / name) for name in sorted(paths)},
            "loaded_checkout_module_origins": dict(sorted(origins.items())),
            "runtime": {"python": platform.python_version(), "sqlite": sqlite3.sqlite_version,
                        "executable_sha256": stream_sha256(Path(sys.executable).resolve()),
                        "packages": dict(sorted((d.metadata["Name"], d.version)
                                                for d in importlib.metadata.distributions()
                                                if d.metadata["Name"]))},
            "historical_execution_source_reconstructed": False}


def validate_source_binding(expected: dict, actual: dict) -> list[str]:
    failures = []
    for key in ("schema", "files", "runtime", "production_git_tree"):
        if key not in expected or expected[key] != actual.get(key):
            failures.append(f"source_binding_mismatch:{key}")
    # HEAD is recorded separately: committing identical executable bytes after
    # preparation legitimately changes it. File/hash equality remains mandatory.
    for name, location in actual["loaded_checkout_module_origins"].items():
        prior_origin = expected.get("loaded_checkout_module_origins", {}).get(name)
        if prior_origin is not None and prior_origin != location:
            failures.append(f"loaded_module_origin_changed:{name}")
        if actual["files"].get(location) != expected.get("files", {}).get(location):
            failures.append(f"loaded_module_not_bound:{name}")
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    # Match the real auditor's loaded dependency closure without accessing data.
    from tools import umbra_baseline_audit  # noqa: F401
    binding = capture_source_binding()
    digest = publish_json_once(args.output, binding)
    print(json.dumps({"sha256": digest, "bound_files": len(binding["files"]),
                      "historical_execution_source_reconstructed": False}))


if __name__ == "__main__":
    main()
