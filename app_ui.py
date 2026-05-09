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


def load_schedules() -> tuple[list[object], list[dict[str, object]]]:
    raw_data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    schedules = parse_schedule_file(raw_data)
    ordered = sorted(schedules, key=lambda item: item.start)
    return ordered, [schedule_to_dict(schedule) for schedule in ordered]


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

st.markdown(
    """
    <style>
    .stApp {
        background: #f7f9fc;
        color: #191f28;
    }
    [data-testid="stHeader"] {
        background: rgba(247, 249, 252, 0.85);
    }
    .main .block-container {
        max-width: 1040px;
        padding-top: 2.5rem;
        padding-bottom: 3rem;
    }
    h1, h2, h3 {
        letter-spacing: 0;
    }
    .hero {
        background: #ffffff;
        border: 1px solid #e5e8ef;
        border-radius: 24px;
        padding: 34px 36px;
        box-shadow: 0 20px 48px rgba(25, 31, 40, 0.06);
        margin-bottom: 22px;
    }
    .eyebrow {
        color: #3182f6;
        font-size: 15px;
        font-weight: 700;
        margin-bottom: 14px;
    }
    .hero-title {
        color: #191f28;
        font-size: 42px;
        line-height: 1.18;
        font-weight: 800;
        margin-bottom: 14px;
    }
    .hero-copy {
        color: #4e5968;
        font-size: 18px;
        line-height: 1.6;
        margin-bottom: 0;
    }
    .section-title {
        color: #191f28;
        font-size: 24px;
        font-weight: 800;
        margin: 30px 0 12px;
    }
    .soft-card {
        background: #ffffff;
        border: 1px solid #e5e8ef;
        border-radius: 20px;
        padding: 22px 24px;
        box-shadow: 0 12px 30px rgba(25, 31, 40, 0.04);
        height: 100%;
    }
    .metric-label {
        color: #8b95a1;
        font-size: 14px;
        font-weight: 700;
        margin-bottom: 8px;
    }
    .metric-value {
        color: #191f28;
        font-size: 30px;
        font-weight: 800;
        line-height: 1.2;
    }
    .metric-sub {
        color: #6b7684;
        font-size: 14px;
        margin-top: 8px;
        line-height: 1.5;
    }
    .timeline-item {
        background: #ffffff;
        border: 1px solid #e5e8ef;
        border-radius: 18px;
        padding: 18px 20px;
        margin-bottom: 10px;
    }
    .timeline-time {
        color: #3182f6;
        font-size: 14px;
        font-weight: 800;
        margin-bottom: 6px;
    }
    .timeline-title {
        color: #191f28;
        font-size: 18px;
        font-weight: 800;
        margin-bottom: 6px;
    }
    .timeline-meta {
        color: #6b7684;
        font-size: 14px;
        line-height: 1.5;
    }
    .risk-box {
        background: #fff7f0;
        border: 1px solid #ffd8b5;
        border-radius: 18px;
        color: #8a3a00;
        padding: 18px 20px;
        font-weight: 700;
        line-height: 1.6;
    }
    .action-item {
        background: #eef6ff;
        border: 1px solid #cfe5ff;
        border-radius: 16px;
        color: #1b64da;
        padding: 16px 18px;
        margin-bottom: 10px;
        font-weight: 700;
    }
    div.stButton > button {
        width: 100%;
        border-radius: 16px;
        min-height: 54px;
        font-size: 17px;
        font-weight: 800;
        background: #3182f6;
        border: 0;
    }
    div.stButton > button:hover {
        background: #1b64da;
        border: 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">오늘의 캘린더 브리핑</div>
      <div class="hero-title">일정을 넣으면<br>하루의 리스크와 우선순위가 바로 보입니다</div>
      <p class="hero-copy">캘린더 데이터를 분석해 사용자 페르소나, 일정 충돌, 전환 시간 부족, 추천 액션을 한 화면에서 정리합니다.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

ordered_schedules, schedule_rows = load_schedules()

preview_analysis = analyze_schedule(ordered_schedules)
preview_persona = classify_persona(preview_analysis)

metric_columns = st.columns(3)
with metric_columns[0]:
    st.markdown(
        f"""
        <div class="soft-card">
          <div class="metric-label">오늘의 유형</div>
          <div class="metric-value">{preview_persona["name"]}</div>
          <div class="metric-sub">{preview_persona["rationale"]}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with metric_columns[1]:
    st.markdown(
        f"""
        <div class="soft-card">
          <div class="metric-label">전체 일정</div>
          <div class="metric-value">{preview_analysis["total_schedules"]}개</div>
          <div class="metric-sub">오늘 등록된 일정 수입니다.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with metric_columns[2]:
    st.markdown(
        f"""
        <div class="soft-card">
          <div class="metric-label">총 일정 시간</div>
          <div class="metric-value">{preview_analysis["total_scheduled_hours"]}시간</div>
          <div class="metric-sub">캘린더에 이미 배정된 시간입니다.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown('<div class="section-title">일정 타임라인</div>', unsafe_allow_html=True)
for schedule in schedule_rows:
    st.markdown(
        f"""
        <div class="timeline-item">
          <div class="timeline-time">{schedule["start"]} - {schedule["end"]}</div>
          <div class="timeline-title">{schedule["title"]}</div>
          <div class="timeline-meta">{schedule["category"]} · {schedule["location"]}<br>{schedule["notes"]}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with st.expander("표로 일정 보기"):
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

st.markdown('<div class="section-title">데일리 브리핑 만들기</div>', unsafe_allow_html=True)
st.caption("버튼을 누르면 같은 분석 로직으로 오늘의 리스크 메시지와 추천 액션을 생성합니다.")

if st.button("일정 분석하기", type="primary"):
    result = run_analysis()
    analysis = result["analysis"]
    persona = result["persona"]
    briefing = result["briefing"]

    st.markdown('<div class="section-title">데일리 브리핑</div>', unsafe_allow_html=True)
    briefing_columns = st.columns([1, 1])
    with briefing_columns[0]:
        st.markdown(
            f"""
            <div class="soft-card">
              <div class="metric-label">사용자 페르소나</div>
              <div class="metric-value">{persona["name"]}</div>
              <div class="metric-sub">{persona["rationale"]}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with briefing_columns[1]:
        st.markdown(
            f"""
            <div class="soft-card">
              <div class="metric-label">분석 요약</div>
              <div class="metric-value">{analysis["total_schedules"]}개 · {analysis["total_scheduled_hours"]}시간</div>
              <div class="metric-sub">전체 일정 수와 총 일정 시간입니다.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-title">주의할 점</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="risk-box">{briefing["risk_message"]}</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">추천 액션</div>', unsafe_allow_html=True)
    for action in briefing["recommended_actions"]:
        st.markdown(f'<div class="action-item">{action}</div>', unsafe_allow_html=True)
