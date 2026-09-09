#!/usr/bin/env python3
"""Durably publish the reviewed AS-015 external-reference disposition."""

import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY) not in sys.path:
    sys.path.insert(0, str(REPOSITORY))

from tools.as015_evidence import publish


def main() -> None:
    report = Path(__file__).resolve().parents[1] / "docs" / "AS015_EXTERNAL_RECOVERY_PRIOR_ART.md"
    print(publish("AS015_EXTERNAL_RECOVERY_PRIOR_ART.md", report.read_text(encoding="utf-8")))


if __name__ == "__main__":
    main()
