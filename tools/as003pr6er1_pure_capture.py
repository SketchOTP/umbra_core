"""Run the additive R6E-R1 pure tests with durable output capture."""

from __future__ import annotations

import json
import sys

from tools.as003pr6er1_evidence import capture_command


def main() -> None:
    name = sys.argv[1]
    command = sys.argv[2:]
    record = capture_command(name, command, cwd="/home/sketch/Projects/umbra-close02x-work")
    print(json.dumps(record, sort_keys=True))
    raise SystemExit(record["exit_code"])


if __name__ == "__main__":
    main()
