"""Local relative-link audit for the R6E public documentation refresh."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FILES = (ROOT / "README.md", ROOT / "docs" / "EVIDENCE_GUIDE.md")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def main() -> None:
    checked: list[dict[str, str]] = []
    broken: list[dict[str, str]] = []
    for source in FILES:
        for target in LINK_RE.findall(source.read_text()):
            target = target.strip().split("#", 1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            resolved = (source.parent / target).resolve()
            item = {"source": str(source.relative_to(ROOT)), "target": target, "resolved": str(resolved)}
            checked.append(item)
            if not resolved.exists():
                broken.append(item)
    print(json.dumps({"files": [str(path.relative_to(ROOT)) for path in FILES], "checked": len(checked), "broken": broken, "result": "PASS" if not broken else "FAIL"}, sort_keys=True))


if __name__ == "__main__":
    main()
