from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .analyzer import analyze_schedule
from .briefing import generate_briefing
from .encouragement import generate_encouragement
from .persona import classify_persona
from .schema import parse_schedule_file


BASE_DIR = Path(__file__).resolve().parents[1]
SAMPLE_SCHEDULE_PATH = BASE_DIR / "data" / "sample_schedule.json"

app = FastAPI(title="Calendar Briefing API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_sample_schedule() -> dict[str, Any]:
    return json.loads(SAMPLE_SCHEDULE_PATH.read_text(encoding="utf-8"))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/schedule")
def get_schedule() -> dict[str, Any]:
    return load_sample_schedule()


@app.get("/briefing")
def get_briefing() -> dict[str, Any]:
    raw_data = load_sample_schedule()
    schedules = parse_schedule_file(raw_data)
    analysis = analyze_schedule(schedules)
    persona = classify_persona(analysis)
    briefing = generate_briefing(schedules, analysis, persona)
    encouragement = generate_encouragement(analysis, persona)

    return {
        "analysis": analysis,
        "persona": persona,
        "briefing": briefing,
        "encouragement": encouragement,
    }
