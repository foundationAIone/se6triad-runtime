"""Run a minimal SE6Triad runtime packet demo."""

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from se6triad_runtime import build_packet

command = "Launch attention for CommandCenterOS, publish approved posts, capture leads, and measure value."
packet = build_packet(command)

out_path = ROOT / "results" / "runtime_demo_result.json"
out_path.write_text(packet.to_json(), encoding="utf-8")
print(packet.to_json())
