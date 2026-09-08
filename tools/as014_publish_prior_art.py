"""Publish the reviewed AS-014 external-prior-art report as durable evidence."""

from __future__ import annotations

from pathlib import Path

from tools.as014_evidence import publish


def main() -> None:
    report = Path(__file__).resolve().parents[1] / "docs" / "AS014_EXTERNAL_PRIOR_ART.md"
    publish("AS014_EXTERNAL_PRIOR_ART.md", report.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
