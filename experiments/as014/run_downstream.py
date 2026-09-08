"""Literal AS-014 downstream CLI; every result gets a durable checkpoint first."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiments.as014.downstream import VARIANTS, ablation, boundedness, soak
from experiments.as014.publication import publish_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("boundedness", "soak", "ablation"), required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ticks", type=int, default=100_000)
    parser.add_argument("--variant", choices=VARIANTS, default="FULL")
    parser.add_argument("--warmup-seconds", type=float, default=300.0)
    parser.add_argument("--measure-seconds", type=float, default=3600.0)
    parser.add_argument("--preflight-ledger-tail", type=int)
    args = parser.parse_args()
    args.work.mkdir(parents=True, exist_ok=False)
    overrides = None
    if args.preflight_ledger_tail is not None:
        if args.preflight_ledger_tail < 32:
            raise ValueError("preflight_ledger_tail_below_per_tick_bound")
        overrides = {"ledger_hot_tail_event_max": args.preflight_ledger_tail}
    if args.mode == "boundedness":
        result = boundedness(args.seed, args.work, args.ticks, ledger_overrides=overrides)
    elif args.mode == "soak":
        result = soak(
            args.seed,
            args.work,
            warmup_seconds=args.warmup_seconds,
            measure_seconds=args.measure_seconds,
            ledger_overrides=overrides,
        )
    else:
        result = ablation(args.seed, args.work, args.variant, args.ticks, ledger_overrides=overrides)
    result["cli_preflight_ledger_tail"] = args.preflight_ledger_tail
    checkpoint_hash = publish_json(args.checkpoint, result, schema=result["schema"])
    output_hash = publish_json(args.output, result, schema=result["schema"])
    if checkpoint_hash != output_hash:
        raise RuntimeError("AS014_CHECKPOINT_FINAL_HASH_MISMATCH")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
