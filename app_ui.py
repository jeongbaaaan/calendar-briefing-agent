from __future__ import annotations

import json
import sys
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent
APP_DIR = PROJECT_ROOT / "app"
DATA_PATH = PROJECT_ROOT / "data" / "sample_schedule.json"
WEATHER_PATH = PROJECT_ROOT / "data" / "sample_weather.json"

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from analyzer import analyze_schedule
from briefing import generate_briefing
from coach import generate_life_coach_plan
from day_context import build_day_context, parse_weather_file
from persona import classify_persona
from schema import parse_schedule_file, schedule_to_dict


CATEGORY_BADGES = {
    "work": ("업무", "#eef5ff", "#2f6edb"),
    "업무": ("업무", "#eef5ff", "#2f6edb"),
    "meeting": ("업무", "#eef5ff", "#2f6edb"),
    "회의": ("업무", "#eef5ff", "#2f6edb"),
    "client": ("고객", "#fff4e8", "#d77a1f"),
    "고객": ("고객", "#fff4e8", "#d77a1f"),
    "personal": ("개인", "#f5f0ff", "#7a5bd6"),
    "개인": ("개인", "#f5f0ff", "#7a5bd6"),
    "health": ("건강", "#ecfbf2", "#278a55"),
    "건강": ("건강", "#ecfbf2", "#278a55"),
    "exercise": ("건강", "#ecfbf2", "#278a55"),
    "운동": ("건강", "#ecfbf2", "#278a55"),
    "travel": ("여행", "#eef9fb", "#16869a"),
    "여행": ("여행", "#eef9fb", "#16869a"),
    "learning": ("학습", "#fff6f1", "#cf6a45"),
    "학습": ("학습", "#fff6f1", "#cf6a45"),
    "study": ("학습", "#fff6f1", "#cf6a45"),
    "공부": ("학습", "#fff6f1", "#cf6a45"),
    "networking": ("네트워킹", "#f1f7ff", "#3867a8"),
    "네트워킹": ("네트워킹", "#f1f7ff", "#3867a8"),
    "recovery": ("회복", "#f3faf4", "#4a8b5c"),
    "회복": ("회복", "#f3faf4", "#4a8b5c"),
}


def load_schedules() -> list[dict[str, object]]:
    raw_data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    schedules = parse_schedule_file(raw_data)
    return [schedule_to_dict(schedule) for schedule in sorted(schedules, key=lambda item: item.start)]


def load_schedule_metadata() -> dict[str, str]:
    raw_data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return {
        "date": str(raw_data.get("date", "")),
        "timezone": str(raw_data.get("timezone", "")),
    }


def load_weather_metadata() -> dict[str, Any]:
    raw_weather = json.loads(WEATHER_PATH.read_text(encoding="utf-8"))
    return parse_weather_file(raw_weather)


def run_analysis() -> dict[str, object]:
    raw_data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    raw_weather = json.loads(WEATHER_PATH.read_text(encoding="utf-8"))
    schedules = parse_schedule_file(raw_data)
    weather_data = parse_weather_file(raw_weather)
    analysis = analyze_schedule(schedules)
    persona = classify_persona(analysis)
    briefing = generate_briefing(schedules, analysis, persona)
    day_context = build_day_context(schedules, weather_data)
    life_coach = generate_life_coach_plan(analysis, persona, day_context)

    return {
        "analysis": analysis,
        "persona": persona,
        "briefing": briefing,
        "day_context": day_context,
        "life_coach": life_coach,
    }


def format_date_badge(metadata: dict[str, str]) -> str:
    raw_date = metadata["date"]
    timezone = metadata["timezone"]

    if raw_date:
        try:
            parsed_date = datetime.strptime(raw_date, "%Y-%m-%d")
            date_text = f"{parsed_date.year}년 {parsed_date.month}월 {parsed_date.day}일"
        except ValueError:
            date_text = raw_date
    else:
        date_text = "오늘"

    if timezone:
        return f"{date_text} · {timezone}"
    return date_text


def format_time_range(schedule: dict[str, object]) -> str:
    start = str(schedule["start"]).split(" ")[-1]
    end = str(schedule["end"]).split(" ")[-1]
    return f"{start} - {end}"


def format_duration(hours: float) -> str:
    if hours.is_integer():
        return f"{int(hours)}시간"
    return f"{hours:.2f}".rstrip("0").rstrip(".") + "시간"


def get_category_badge(category: object) -> tuple[str, str, str]:
    normalized = str(category).strip().lower()
    return CATEGORY_BADGES.get(normalized, (str(category), "#f4f6f8", "#64748b"))


def render_schedule_card(schedule: dict[str, object]) -> None:
    label, background, color = get_category_badge(schedule["category"])
    location = str(schedule.get("location") or "장소 미정")
    notes = str(schedule.get("notes") or "메모 없음")

    st.markdown(
        f"""
        <article class="schedule-card">
            <div class="schedule-card__top">
                <span class="schedule-time">{escape(format_time_range(schedule))}</span>
                <span class="category-badge" style="background:{background}; color:{color};">
                    {escape(label)}
                </span>
            </div>
            <h3>{escape(str(schedule["title"]))}</h3>
            <p class="schedule-meta">{escape(location)}</p>
            <p class="schedule-notes">{escape(notes)}</p>
        </article>
        """,
        unsafe_allow_html=True,
    )


def render_stat(label: str, value: str) -> str:
    return f"""
    <div class="stat-card">
        <span>{escape(label)}</span>
        <strong>{escape(value)}</strong>
    </div>
    """


def render_text_list(items: list[str]) -> str:
    return "".join(f"<li>{escape(item)}</li>" for item in items)


def render_checklist_items(items: list[dict[str, str]]) -> str:
    rows = []
    for item in items:
        rows.append(
            f"""
            <li class="check-row">
                <span class="check-mark">✓</span>
                <div>
                    <strong>{escape(item["item"])}</strong>
                    <p>{escape(item["reason"])}</p>
                </div>
            </li>
            """
        )
    return "".join(rows)


def clean_warning_text(text: str) -> str:
    return text.replace("리스크", "주의할 점")


st.set_page_config(page_title="오늘 일정 브리핑", layout="wide")

st.markdown(
    """
    <style>
    :root {
        --app-bg: #f7f9fb;
        --text: #1f2937;
        --muted: #6b7280;
        --line: #e7edf3;
        --card: #ffffff;
        --blue: #4d8df7;
        --mint: #62c7a7;
        --coral: #ff806d;
        --yellow-bg: #fff8e7;
        --yellow-line: #ffd88a;
    }

    .stApp {
        background: var(--app-bg);
        color: var(--text);
    }

    .block-container {
        max-width: 1080px;
        padding: 2.25rem 1.25rem 3.5rem;
    }

    h1, h2, h3, p, li, div, span, button {
        letter-spacing: 0;
    }

    h1, h2, h3 {
        color: var(--text);
    }

    .hero {
        background: linear-gradient(135deg, #ffffff 0%, #f2f7ff 52%, #f7fff9 100%);
        border: 1px solid var(--line);
        border-radius: 8px;
        box-shadow: 0 18px 45px rgba(31, 41, 55, 0.07);
        margin-bottom: 1.4rem;
        padding: 2.1rem 2.2rem;
    }

    .brand-badge,
    .date-badge {
        align-items: center;
        border-radius: 999px;
        display: inline-flex;
        font-size: 0.85rem;
        font-weight: 700;
        line-height: 1;
        padding: 0.48rem 0.7rem;
    }

    .brand-badge {
        background: #eaf7f2;
        color: #258060;
        margin-bottom: 0.9rem;
    }

    .date-badge {
        background: #ffffff;
        border: 1px solid var(--line);
        color: #586474;
        margin-top: 1rem;
    }

    .hero h1 {
        font-size: clamp(2.35rem, 6vw, 4rem);
        line-height: 1.03;
        margin: 0 0 0.65rem;
    }

    .hero p {
        color: var(--muted);
        font-size: 1.08rem;
        line-height: 1.65;
        margin: 0;
        max-width: 620px;
    }

    .section-title {
        font-size: 1.15rem;
        font-weight: 800;
        margin: 0.3rem 0 0.9rem;
    }

    .schedule-stack {
        display: flex;
        flex-direction: column;
        gap: 0.85rem;
    }

    .schedule-card,
    .quick-card,
    .result-card {
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 8px;
        box-shadow: 0 12px 30px rgba(31, 41, 55, 0.06);
    }

    .schedule-card {
        margin-bottom: 0.85rem;
        padding: 1.05rem 1.1rem;
    }

    .schedule-card__top {
        align-items: center;
        display: flex;
        justify-content: space-between;
        gap: 0.75rem;
        margin-bottom: 0.65rem;
    }

    .schedule-time {
        color: var(--blue);
        font-size: 0.9rem;
        font-weight: 800;
    }

    .category-badge {
        border-radius: 999px;
        flex: 0 0 auto;
        font-size: 0.78rem;
        font-weight: 800;
        padding: 0.38rem 0.58rem;
    }

    .schedule-card h3 {
        font-size: 1.06rem;
        line-height: 1.35;
        margin: 0 0 0.45rem;
    }

    .schedule-meta {
        color: #536173;
        font-size: 0.9rem;
        font-weight: 700;
        margin: 0 0 0.48rem;
    }

    .schedule-notes {
        color: var(--muted);
        font-size: 0.92rem;
        line-height: 1.55;
        margin: 0;
    }

    .quick-card {
        margin-bottom: 0.95rem;
        padding: 1.2rem;
    }

    .quick-card h3,
    .result-card h3 {
        font-size: 1.05rem;
        margin: 0 0 0.65rem;
    }

    .quick-card p,
    .result-card p,
    .result-card li {
        color: var(--muted);
        font-size: 0.95rem;
        line-height: 1.58;
    }

    .quick-card p,
    .result-card p {
        margin: 0;
    }

    .stat-grid {
        display: grid;
        gap: 0.65rem;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        margin: 1rem 0;
    }

    .stat-card {
        background: #f8fafc;
        border: 1px solid #edf2f7;
        border-radius: 8px;
        padding: 0.85rem;
    }

    .stat-card span {
        color: var(--muted);
        display: block;
        font-size: 0.78rem;
        font-weight: 700;
        margin-bottom: 0.24rem;
    }

    .stat-card strong {
        color: var(--text);
        font-size: 1.22rem;
    }

    div.stButton > button:first-child {
        background: var(--coral);
        border: 0;
        border-radius: 8px;
        color: #ffffff;
        font-weight: 800;
        min-height: 3rem;
        padding: 0.75rem 1rem;
        width: 100%;
    }

    div.stButton > button:first-child:hover {
        background: #f06b58;
        border: 0;
        color: #ffffff;
    }

    .result-card {
        min-height: 100%;
        margin-bottom: 1rem;
        padding: 1.15rem 1.2rem;
    }

    .result-card--calm {
        border-left: 4px solid var(--mint);
    }

    .result-card--notice {
        background: var(--yellow-bg);
        border-color: var(--yellow-line);
        border-left: 4px solid #f4b740;
    }

    .result-card--blue {
        border-left: 4px solid var(--blue);
    }

    .result-card ul {
        list-style: none;
        margin: 0.3rem 0 0;
        padding: 0;
    }

    .result-card li {
        margin-bottom: 0.55rem;
    }

    .check-row {
        align-items: flex-start;
        display: flex;
        gap: 0.65rem;
    }

    .check-row p {
        margin-top: 0.16rem;
    }

    .check-mark {
        align-items: center;
        background: #eaf7f2;
        border-radius: 999px;
        color: #258060;
        display: inline-flex;
        flex: 0 0 auto;
        font-size: 0.8rem;
        font-weight: 900;
        height: 1.35rem;
        justify-content: center;
        width: 1.35rem;
    }

    .weather-line {
        background: #f7fbff;
        border: 1px solid #e4efff;
        border-radius: 8px;
        color: #426180;
        font-size: 0.9rem;
        font-weight: 700;
        margin-top: 0.9rem;
        padding: 0.75rem 0.85rem;
    }

    @media (max-width: 760px) {
        .hero {
            padding: 1.45rem;
        }

        .stat-grid {
            grid-template-columns: 1fr;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

schedule_rows = load_schedules()
schedule_metadata = load_schedule_metadata()
weather_metadata = load_weather_metadata()
total_hours = sum(float(schedule["duration_hours"]) for schedule in schedule_rows)
weather = weather_metadata["weather"]

st.markdown(
    f"""
    <section class="hero">
        <span class="brand-badge">아 맞다,</span>
        <h1>오늘 일정 브리핑</h1>
        <p>오늘 하루의 흐름과 미리 챙길 점을 한눈에 정리해드려요.</p>
        <span class="date-badge">{escape(format_date_badge(schedule_metadata))}</span>
    </section>
    """,
    unsafe_allow_html=True,
)

left_column, right_column = st.columns([1.45, 0.95], gap="large")

with left_column:
    st.markdown('<h2 class="section-title">오늘 일정</h2>', unsafe_allow_html=True)
    st.markdown('<div class="schedule-stack">', unsafe_allow_html=True)
    for schedule in schedule_rows:
        render_schedule_card(schedule)
    st.markdown("</div>", unsafe_allow_html=True)

with right_column:
    st.markdown(
        f"""
        <aside class="quick-card">
            <h3>한눈에 보기</h3>
            <p>일정 밀도와 날씨를 함께 보고 오늘의 흐름을 가볍게 점검해요.</p>
            <div class="stat-grid">
                {render_stat("일정 수", str(len(schedule_rows)))}
                {render_stat("예정된 시간", format_duration(total_hours))}
            </div>
            <div class="weather-line">
                {escape(weather_metadata["location"])} · {escape(weather["summary"])}
            </div>
        </aside>
        """,
        unsafe_allow_html=True,
    )

    if st.button("오늘 일정 분석하기", type="primary", width="stretch"):
        st.session_state["briefing_result"] = run_analysis()

result = st.session_state.get("briefing_result")

if result:
    analysis = result["analysis"]
    persona = result["persona"]
    briefing = result["briefing"]
    day_context = result["day_context"]
    life_coach = result["life_coach"]
    result_weather = day_context["weather"]["weather"]

    st.markdown('<h2 class="section-title">브리핑 결과</h2>', unsafe_allow_html=True)
    top_left, top_right = st.columns(2, gap="medium")

    with top_left:
        st.markdown(
            f"""
            <section class="result-card result-card--calm">
                <h3>오늘 하루 요약</h3>
                <p>{escape(life_coach["headline"])}</p>
                <div class="stat-grid">
                    {render_stat("일정 수", str(analysis["total_schedules"]))}
                    {render_stat("예정된 시간", format_duration(float(analysis["total_scheduled_hours"])))}
                </div>
                <p>{escape(day_context["weather"]["location"])} · {escape(result_weather["summary"])}</p>
            </section>
            """,
            unsafe_allow_html=True,
        )

    with top_right:
        st.markdown(
            f"""
            <section class="result-card result-card--notice">
                <h3>조심할 점</h3>
                <p>{escape(clean_warning_text(briefing["risk_message"]))}</p>
            </section>
            """,
            unsafe_allow_html=True,
        )

    bottom_left, bottom_right = st.columns(2, gap="medium")

    with bottom_left:
        prep_items = life_coach["prep_checklist"]
        st.markdown(
            f"""
            <section class="result-card result-card--blue">
                <h3>미리 챙기면 좋은 것</h3>
                <ul>{render_checklist_items(prep_items)}</ul>
                <ul>{render_text_list(briefing["recommended_actions"])}</ul>
            </section>
            """,
            unsafe_allow_html=True,
        )

    with bottom_right:
        st.markdown(
            f"""
            <section class="result-card result-card--calm">
                <h3>나의 일정 유형</h3>
                <p><strong>{escape(persona["name"])}</strong></p>
                <p>{escape(persona["rationale"])}</p>
            </section>
            """,
            unsafe_allow_html=True,
        )
