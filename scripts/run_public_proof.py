"""Run the SE6Triad public proof summary.

This script intentionally uses only the Python standard library.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from se6triad_runtime import build_packet, estimate_tokens_char  # noqa: E402


def main() -> None:
    user_command = "Launch attention for CommandCenterOS, publish approved posts, capture leads, and measure value."
    packet = build_packet(user_command)

    normal_context = (ROOT / "results" / "compression_result.json").read_text(encoding="utf-8")
    compression = json.loads(normal_context)

    summary = {
        "project": "SE6Triad: A State-Loop Runtime for Agentic LLMs",
        "core_loop": "Observe → Reflect → Classify → Constrain → Route → Act → Audit → Learn",
        "runtime_packet_estimated_tokens": estimate_tokens_char(packet.to_json()),
        "compression_result": compression,
        "reference_product": "CommandCenterOS",
        "honest_claim": "This public demo proves context/state compression potential, not production API billing reduction yet.",
    }

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
