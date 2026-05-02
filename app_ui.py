from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent
APP_DIR = PROJECT_ROOT / "app"
DATA_PATH = PROJECT_ROOT / "data" / "sample_schedule.json"

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from analyzer import analyze_schedule
from briefing import generate_briefing
from persona import classify_persona
from schema import parse_schedule_file, schedule_to_dict


def load_schedules() -> list[dict[str, object]]:
    raw_data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    schedules = parse_schedule_file(raw_data)
    return [schedule_to_dict(schedule) for schedule in sorted(schedules, key=lambda item: item.start)]


def run_analysis() -> dict[str, object]:
    raw_data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    schedules = parse_schedule_file(raw_data)
    analysis = analyze_schedule(schedules)
    persona = classify_persona(analysis)
    briefing = generate_briefing(schedules, analysis, persona)

    return {
        "analysis": analysis,
        "persona": persona,
        "briefing": briefing,
    }


st.set_page_config(page_title="Calendar Briefing Agent", layout="wide")

st.title("Calendar Briefing Agent")
st.caption("Local MVP for schedule analysis, persona classification, and daily briefing generation.")

st.subheader("Schedule")
schedule_rows = load_schedules()
st.dataframe(
    schedule_rows,
    use_container_width=True,
    hide_index=True,
    column_order=["title", "category", "start", "end", "duration_hours", "location", "notes"],
)

if st.button("Analyze Schedule", type="primary"):
    result = run_analysis()
    analysis = result["analysis"]
    persona = result["persona"]
    briefing = result["briefing"]

    st.subheader("Briefing")
    st.metric("Persona", persona["name"])
    st.write(persona["rationale"])

    metric_columns = st.columns(2)
    metric_columns[0].metric("Total Schedules", analysis["total_schedules"])
    metric_columns[1].metric("Total Scheduled Hours", analysis["total_scheduled_hours"])

    st.warning(briefing["risk_message"])

    st.subheader("Recommended Actions")
    for action in briefing["recommended_actions"]:
        st.markdown(f"- {action}")
