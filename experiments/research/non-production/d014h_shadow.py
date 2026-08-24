from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from d014h_regulation import canonical_bytes, evaluate
from d014h_replay import replay_twice, synthetic_fixture


def run_trace(input_path: Path, output_path: Path) -> dict:
    rows = []
    with input_path.open("rb") as source, output_path.open("wb") as target:
        for index, raw in enumerate(source):
            if not raw.strip():
                continue
            payload = json.loads(raw)
            result = evaluate(payload)
            row = {
                "decision_index": index,
                "input_fingerprint": result["input_fingerprint"],
                "output": result,
            }
            target.write(canonical_bytes(row) + b"\\n")
            rows.append(row["output"]["output_fingerprint"])
    return {"rows": len(rows), "output_fingerprints": rows}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("synthetic-replay", "trace"))
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.mode == "synthetic-replay":
        print(json.dumps(replay_twice(synthetic_fixture()), sort_keys=True))
        return
    if args.input is None or args.output is None:
        raise SystemExit("--input and --output are required for trace mode")
    print(json.dumps(run_trace(args.input, args.output), sort_keys=True))


if __name__ == "__main__":
    main()
