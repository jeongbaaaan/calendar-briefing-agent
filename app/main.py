from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from analyzer import analyze_schedule
from briefing import generate_briefing
from persona import classify_persona
from schema import parse_schedule_file


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "sample_schedule.json"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "logs" / "result.json"


def run(
    input_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> dict[str, Any]:
    raw_data = json.loads(input_path.read_text(encoding="utf-8"))
    schedules = parse_schedule_file(raw_data)

    analysis = analyze_schedule(schedules)
    persona = classify_persona(analysis)
    briefing = generate_briefing(schedules, analysis, persona)

    result = {
        "input_file": str(input_path),
        "analysis": analysis,
        "briefing": briefing,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


if __name__ == "__main__":
    generated = run()
    print(f"Daily briefing generated: {DEFAULT_OUTPUT_PATH}")
    print(generated["briefing"]["summary"])
