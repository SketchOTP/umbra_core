#!/usr/bin/env python3
"""Read-only retained R5 root attestation for UMBRA-AS-003P-R5A."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.as003pr5a.protocol import retained_root_attestation


result = retained_root_attestation()
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if result["result"] == "PASS" else 1)
