"""Finite resource observation plus separate Atlas export; never retries execution."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shlex
import subprocess
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.as017_evidence import publish_json_once, stream_sha256
from tools.umbra_resource_probe import run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--candidate-commit", required=True)
    parser.add_argument("--protocol-sha256", required=True)
    parser.add_argument("--durable-host", required=True)
    parser.add_argument("--durable-path", required=True)
    args = parser.parse_args()
    if args.durable_host != "atlas-laptop" or not args.durable_path.startswith(
            "/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-resource-"):
        raise ValueError("durable_destination_outside_authorized_evidence_scope")
    remote = shlex.quote(args.durable_path)
    # Reserve a fresh destination before execution. No deletion or overwrite.
    subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", args.durable_host,
        f"test ! -e {remote} && mkdir {remote}"], check=True)
    report = run(args.work.resolve(), args.candidate_commit, args.protocol_sha256)
    # Local result is sealed before publication. A failed export never reruns it.
    files = sorted(path for path in args.work.rglob("*") if path.is_file())
    expected = {path.relative_to(args.work).as_posix(): stream_sha256(path) for path in files}
    try:
        subprocess.run(["scp", "-q", "-r", str(args.work.resolve()) + "/.",
                        f"{args.durable_host}:{args.durable_path}/"], check=True)
        names = " ".join(shlex.quote(name) for name in expected)
        output = subprocess.check_output(["ssh", "-o", "BatchMode=yes", args.durable_host,
            f"cd {remote} && sha256sum -- {names}"], text=True)
        observed = dict((line.split(maxsplit=1)[1].lstrip(" *"), line.split(maxsplit=1)[0])
                        for line in output.splitlines())
        if observed != expected:
            raise ValueError("durable_export_hash_mismatch")
        receipt = {"status": "DURABLE_EXPORT_VERIFIED", "host": args.durable_host,
                   "path": args.durable_path, "hashes": expected,
                   "execution_retries": 0, "scientific_qualification": False}
    except Exception as exc:
        receipt = {"status": "LOCAL_SEALED_EXPORT_PENDING", "error": repr(exc),
                   "host": args.durable_host, "path": args.durable_path,
                   "hashes": expected, "execution_retries": 0}
    publish_json_once(args.work / "delivery.json", receipt)
    print(json.dumps({"observation_verdict": report["verdict"], "ticks": report["ticks"],
                      "delivery": receipt["status"], "work": str(args.work)}, sort_keys=True))
    raise SystemExit(0 if report["verdict"] == "OBSERVATION_COMPLETE" and
                     receipt["status"] == "DURABLE_EXPORT_VERIFIED" else 1)


if __name__ == "__main__":
    main()
