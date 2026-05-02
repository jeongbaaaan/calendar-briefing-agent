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


st.set_page_config(page_title="캘린더 브리핑 에이전트", layout="wide")

st.title("캘린더 브리핑 에이전트")
st.caption("일정 데이터를 분석해 사용자 페르소나와 데일리 브리핑을 생성하는 로컬 최소 기능 제품입니다.")

st.subheader("일정 목록")
schedule_rows = load_schedules()
st.dataframe(
    schedule_rows,
    width="stretch",
    hide_index=True,
    column_order=["title", "category", "start", "end", "duration_hours", "location", "notes"],
    column_config={
        "title": "일정명",
        "category": "카테고리",
        "start": "시작 시간",
        "end": "종료 시간",
        "duration_hours": "소요 시간",
        "location": "장소",
        "notes": "메모",
    },
)

if st.button("일정 분석하기", type="primary"):
    result = run_analysis()
    analysis = result["analysis"]
    persona = result["persona"]
    briefing = result["briefing"]

    st.subheader("데일리 브리핑")
    st.metric("사용자 페르소나", persona["name"])
    st.write(persona["rationale"])

    metric_columns = st.columns(2)
    metric_columns[0].metric("전체 일정 수", analysis["total_schedules"])
    metric_columns[1].metric("총 일정 시간", analysis["total_scheduled_hours"])

    st.warning(briefing["risk_message"])

    st.subheader("추천 액션")
    for action in briefing["recommended_actions"]:
        st.markdown(f"- {action}")
