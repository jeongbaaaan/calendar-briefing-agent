from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_ROOT / "app"
DATA_PATH = PROJECT_ROOT / "data" / "sample_schedule.json"

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from analyzer import analyze_schedule
from briefing import generate_briefing
from main import run
from persona import classify_persona
from schema import parse_schedule_file


class CalendarBriefingTests(unittest.TestCase):
    def test_sample_schedule_generates_expected_analysis(self) -> None:
        raw_data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        schedules = parse_schedule_file(raw_data)

        analysis = analyze_schedule(schedules)
        persona = classify_persona(analysis)
        briefing = generate_briefing(schedules, analysis, persona)

        self.assertEqual(analysis["total_schedules"], 6)
        self.assertEqual(analysis["total_scheduled_hours"], 6.58)
        self.assertEqual(
            analysis["category_distribution"],
            {"건강": 1, "고객": 1, "네트워킹": 1, "업무": 2, "학습": 1},
        )
        self.assertEqual(
            analysis["schedule_conflicts"],
            [
                {
                    "first": "제품 지표 리뷰",
                    "second": "고객 인터뷰",
                    "overlap_minutes": 15,
                }
            ],
        )
        self.assertEqual(len(analysis["insufficient_buffer_time"]), 2)
        self.assertEqual(persona["name"], "업무 집중형 플래너")
        self.assertIn("겹치는 일정 1건", briefing["risk_message"])

    def test_run_records_project_relative_input_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "result.json"

            result = run(output_path=output_path)
            saved_result = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(result["input_file"], "data/sample_schedule.json")
        self.assertEqual(saved_result["input_file"], "data/sample_schedule.json")
        self.assertEqual(result["weather_file"], "data/sample_weather.json")
        self.assertEqual(saved_result["weather_file"], "data/sample_weather.json")
        self.assertEqual(result["day_context"]["outdoor"]["count"], 1)
        self.assertEqual(result["life_coach"]["signals"]["energy_level"], "보통")
        self.assertIn("선크림", [item["item"] for item in result["life_coach"]["prep_checklist"]])


if __name__ == "__main__":
    unittest.main()
