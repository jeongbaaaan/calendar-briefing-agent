from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from analyzer import analyze_schedule
from briefing import generate_briefing
from coach import generate_life_coach_plan
from day_context import build_day_context, parse_weather_file
from persona import classify_persona
from schema import parse_schedule_file


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "sample_schedule.json"
DEFAULT_WEATHER_PATH = PROJECT_ROOT / "data" / "sample_weather.json"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "logs" / "result.json"


def _format_project_path(path: Path) -> str:
    resolved_path = path.resolve()

    try:
        return str(resolved_path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def run(
    input_path: Path = DEFAULT_INPUT_PATH,
    weather_path: Path = DEFAULT_WEATHER_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> dict[str, Any]:
    raw_data = json.loads(input_path.read_text(encoding="utf-8"))
    raw_weather = json.loads(weather_path.read_text(encoding="utf-8"))
    schedules = parse_schedule_file(raw_data)
    weather_data = parse_weather_file(raw_weather)

    analysis = analyze_schedule(schedules)
    persona = classify_persona(analysis)
    briefing = generate_briefing(schedules, analysis, persona)
    day_context = build_day_context(schedules, weather_data)
    life_coach = generate_life_coach_plan(analysis, persona, day_context)

    result = {
        "input_file": _format_project_path(input_path),
        "weather_file": _format_project_path(weather_path),
        "analysis": analysis,
        "briefing": briefing,
        "day_context": day_context,
        "life_coach": life_coach,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    generated = run()
    print(f"Daily briefing generated: {DEFAULT_OUTPUT_PATH}")
    print(generated["life_coach"]["headline"])
