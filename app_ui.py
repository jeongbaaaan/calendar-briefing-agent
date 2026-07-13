from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, time
from pathlib import Path
from uuid import uuid4

import streamlit as st

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass


PROJECT_ROOT = Path(__file__).resolve().parent
APP_DIR = PROJECT_ROOT / "app"
DATA_PATH = PROJECT_ROOT / "data" / "sample_schedule.json"
DATETIME_FORMAT = "%Y-%m-%d %H:%M"

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from analyzer import analyze_schedule
from briefing import generate_briefing
from persona import classify_persona
from schema import parse_schedule_file, schedule_to_dict
from wellness import analyze_wellness
import secretary


CATEGORY_OPTIONS = ["업무", "회의", "고객", "운영", "학습", "네트워킹", "건강", "개인", "가족"]

ENERGY_COLORS = {
    "피크": "#22c55e",
    "보통": "#f59e0b",
    "저하": "#ef4444",
}


# ─── Data helpers ────────────────────────────────────────────────────────────

def load_raw_data() -> dict:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def save_raw_data(raw_data: dict) -> None:
    DATA_PATH.write_text(json.dumps(raw_data, indent=2, ensure_ascii=False), encoding="utf-8")


def get_schedule_models(items: list[dict]) -> list:
    raw = {
        "date": st.session_state.schedule_date.isoformat(),
        "timezone": st.session_state.raw_data.get("timezone", "Asia/Seoul"),
        "schedules": items,
    }
    return sorted(parse_schedule_file(raw), key=lambda s: s.start)


def get_schedule_rows(items: list[dict]) -> list[dict]:
    return [schedule_to_dict(s) for s in get_schedule_models(items)]


def schedules_for_date(items: list[dict], target: date) -> list[dict]:
    return [
        item for item in items
        if datetime.strptime(str(item["start"]), DATETIME_FORMAT).date() == target
    ]


# ─── State ───────────────────────────────────────────────────────────────────

def initialize_state() -> None:
    if "raw_data" not in st.session_state:
        raw_data = load_raw_data()
        st.session_state.raw_data = raw_data
        st.session_state.schedule_items = list(raw_data.get("schedules", []))
        st.session_state.schedule_date = datetime.strptime(str(raw_data.get("date")), "%Y-%m-%d").date()


# ─── Schedule mutations ───────────────────────────────────────────────────────

def add_schedule(title, category, selected_date, start_time, end_time, location, notes) -> tuple[bool, str]:
    start_dt = datetime.combine(selected_date, start_time)
    end_dt = datetime.combine(selected_date, end_time)
    if not title.strip():
        return False, "일정명을 입력해주세요."
    if end_dt <= start_dt:
        return False, "종료 시간은 시작 시간보다 뒤여야 합니다."
    st.session_state.schedule_items.append({
        "id": f"evt-{uuid4().hex[:8]}",
        "title": title.strip(),
        "category": category,
        "start": start_dt.strftime(DATETIME_FORMAT),
        "end": end_dt.strftime(DATETIME_FORMAT),
        "location": location.strip() or "미정",
        "notes": notes.strip() or "메모 없음",
    })
    return True, "일정이 추가되었습니다."


def remove_schedule(schedule_id: str) -> None:
    st.session_state.schedule_items = [
        item for item in st.session_state.schedule_items if item.get("id") != schedule_id
    ]


def persist_current_data() -> None:
    st.session_state.raw_data["date"] = st.session_state.schedule_date.isoformat()
    st.session_state.raw_data["schedules"] = st.session_state.schedule_items
    save_raw_data(st.session_state.raw_data)


# ─── UI components ────────────────────────────────────────────────────────────

def render_schedule_card(schedule: dict) -> None:
    with st.container(border=True):
        cols = st.columns([3, 1])
        with cols[0]:
            st.markdown(f"**{schedule['title']}**")
            st.caption(f"{schedule['start']} - {schedule['end']}")
        with cols[1]:
            if st.button("삭제", key=f"delete-{schedule['id']}"):
                remove_schedule(str(schedule["id"]))
                st.rerun()
        st.write(f"{schedule['category']} · {schedule['location']}")
        st.caption(str(schedule["notes"]))


def render_energy_timeline(energy_curve: list[dict], schedules: list) -> None:
    """Visual energy bar timeline with scheduled events overlaid."""
    if not energy_curve:
        return

    st.markdown("#### 오늘의 에너지 흐름")

    day_start = 7.0
    day_end = 22.0
    day_span = day_end - day_start

    bar_html_parts = []
    for window in energy_curve:
        h_start = max(window["hour_start"], day_start)
        h_end = min(window["hour_end"], day_end)
        if h_end <= h_start:
            continue
        left_pct = (h_start - day_start) / day_span * 100
        width_pct = (h_end - h_start) / day_span * 100
        color = ENERGY_COLORS.get(window["label"], "#9ca3af")
        opacity = 0.25 if window["label"] == "저하" else 0.15
        label = window["label"]
        desc = window["description"]
        bar_html_parts.append(
            f'<div style="position:absolute;left:{left_pct:.2f}%;width:{width_pct:.2f}%;'
            f'height:100%;background:{color};opacity:{opacity};border-radius:4px;" '
            f'title="{label}: {desc}"></div>'
        )

    # Schedule event markers
    event_html_parts = []
    for s in schedules:
        h_start = s.start.hour + s.start.minute / 60
        h_end = s.end.hour + s.end.minute / 60
        left_pct = max(0, (h_start - day_start) / day_span * 100)
        width_pct = max(1, (h_end - h_start) / day_span * 100)
        event_html_parts.append(
            f'<div style="position:absolute;left:{left_pct:.2f}%;width:{width_pct:.2f}%;'
            f'height:100%;background:#6366f1;opacity:0.75;border-radius:3px;'
            f'border:1px solid #4f46e5;" title="{s.title}"></div>'
        )

    hour_labels = "".join(
        f'<span style="position:absolute;left:{(h - day_start) / day_span * 100:.1f}%;'
        f'font-size:10px;color:#9ca3af;transform:translateX(-50%);">{h}시</span>'
        for h in range(int(day_start), int(day_end) + 1, 2)
    )

    legend = "".join(
        f'<span style="display:inline-flex;align-items:center;gap:4px;margin-right:12px;font-size:12px;">'
        f'<span style="width:12px;height:12px;background:{color};border-radius:2px;display:inline-block;"></span>'
        f'{label}</span>'
        for label, color in ENERGY_COLORS.items()
    ) + (
        '<span style="display:inline-flex;align-items:center;gap:4px;font-size:12px;">'
        '<span style="width:12px;height:12px;background:#6366f1;border-radius:2px;display:inline-block;"></span>'
        '내 일정</span>'
    )

    html = f"""
    <div style="margin-bottom:8px;">{legend}</div>
    <div style="position:relative;height:32px;background:#f1f5f9;border-radius:6px;overflow:hidden;margin-bottom:4px;">
        {"".join(bar_html_parts)}
        {"".join(event_html_parts)}
    </div>
    <div style="position:relative;height:16px;">{hour_labels}</div>
    """
    st.html(html)


def render_wellness_risks(wellness: dict) -> None:
    fatigue = wellness.get("fatigue_risks", [])
    meals = wellness.get("meal_risks", [])
    travel = wellness.get("travel_risks", [])
    bio = wellness.get("biorhythm_mismatches", [])

    all_risks = (
        [("🔴", r["description"]) for r in fatigue]
        + [("🍽️", r["description"]) for r in meals]
        + [("🚶", r["description"]) for r in travel]
        + [("⚡", m) for m in bio]
    )

    if not all_risks:
        st.success("오늘 건강·컨디션 리스크가 발견되지 않았습니다.")
        return

    for icon, desc in all_risks:
        st.warning(f"{icon} {desc}")

    if not wellness.get("has_movement"):
        st.info("🏃 오늘 운동/신체 활동 일정이 없습니다. 짧은 산책이라도 추가해보세요.")

    if wellness.get("screen_heavy"):
        st.info("👁️ 화면 기반 일정이 많은 날입니다. 20-20-20 법칙을 실천하세요.")


# ─── Main ─────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="캘린더 브리핑 에이전트", layout="wide", page_icon="📅")
initialize_state()

# ── Sidebar: API key & settings ───────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ 설정")

    env_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if env_key:
        st.success("Claude API 키가 환경 변수에서 감지되었습니다.")
        active_api_key = env_key
    else:
        input_key = st.text_input(
            "Anthropic API 키",
            type="password",
            placeholder="sk-ant-...",
            help="https://console.anthropic.com 에서 발급받은 API 키를 입력하세요.",
        )
        if input_key.strip():
            os.environ["ANTHROPIC_API_KEY"] = input_key.strip()
            active_api_key = input_key.strip()
            st.success("API 키가 적용되었습니다.")
        else:
            active_api_key = ""
            st.info("API 키를 입력하면 Claude AI 브리핑이 활성화됩니다.")

    st.divider()
    st.caption("모델: claude-sonnet-4-6")
    st.caption("브리핑은 AI 비서 브리핑 탭에서 생성하세요.")

st.title("📅 캘린더 브리핑 에이전트")
st.caption("일정을 입력하면 AI 개인 비서가 건강·컨디션·바이오리듬·이동 경로를 챙겨드립니다.")

selected_date = st.date_input("브리핑 날짜", value=st.session_state.schedule_date)
st.session_state.schedule_date = selected_date

selected_items = schedules_for_date(st.session_state.schedule_items, selected_date)
selected_models = get_schedule_models(selected_items)
selected_rows = get_schedule_rows(selected_items)

analysis = analyze_schedule(selected_models) if selected_models else None
persona = classify_persona(analysis) if analysis else None

# Top metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("날짜", selected_date.strftime("%Y-%m-%d"))
col2.metric("일정 수", analysis["total_schedules"] if analysis else 0)
col3.metric("총 시간", f"{analysis['total_scheduled_hours']}h" if analysis else "0h")
col4.metric("오늘의 유형", persona["name"] if persona else "일정 없음")

calendar_tab, secretary_tab, analysis_tab = st.tabs(["📆 캘린더", "🤖 AI 비서 브리핑", "📊 일정 분석"])


# ─── Tab 1: Calendar ─────────────────────────────────────────────────────────

with calendar_tab:
    input_col, list_col = st.columns([1, 1.4])

    with input_col:
        st.subheader("일정 추가")
        with st.form("schedule-form", clear_on_submit=True):
            title = st.text_input("일정명", placeholder="예: 고객 인터뷰")
            category = st.selectbox("카테고리", CATEGORY_OPTIONS)
            start_time = st.time_input("시작 시간", value=time(9, 0), step=900)
            end_time = st.time_input("종료 시간", value=time(10, 0), step=900)
            location = st.text_input("장소", placeholder="예: 구글 미트 / 강남역 / 회의실 A")
            notes = st.text_area("메모", placeholder="준비하거나 확인할 내용을 적어주세요.")
            submitted = st.form_submit_button("일정 추가하기", type="primary")

        if submitted:
            ok, message = add_schedule(title, category, selected_date, start_time, end_time, location, notes)
            if ok:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

        st.divider()
        if st.button("현재 일정 저장하기"):
            persist_current_data()
            st.success("저장 완료.")

    with list_col:
        st.subheader("일정 목록")
        if not selected_rows:
            st.info("선택한 날짜에 일정이 없습니다. 왼쪽에서 추가해보세요.")
        else:
            for schedule in selected_rows:
                render_schedule_card(schedule)
            with st.expander("표로 보기"):
                st.dataframe(
                    selected_rows,
                    hide_index=True,
                    column_order=["title", "category", "start", "end", "duration_hours", "location", "notes"],
                    column_config={
                        "title": "일정명",
                        "category": "카테고리",
                        "start": "시작",
                        "end": "종료",
                        "duration_hours": "시간(h)",
                        "location": "장소",
                        "notes": "메모",
                    },
                )


# ─── Tab 2: AI Secretary Briefing ────────────────────────────────────────────

with secretary_tab:
    st.subheader("🤖 AI 개인 비서 브리핑")
    st.caption("오늘 컨디션을 입력하면 건강·바이오리듬·이동 경로까지 챙겨드립니다.")

    if not selected_models:
        st.info("브리핑을 받으려면 먼저 일정을 추가해주세요.")
    else:
        # Condition input
        with st.expander("오늘 컨디션 입력 (선택)", expanded=True):
            cond_col1, cond_col2 = st.columns(2)
            with cond_col1:
                sleep_hours = st.slider(
                    "어젯밤 수면 시간",
                    min_value=3.0,
                    max_value=10.0,
                    value=7.0,
                    step=0.5,
                    format="%.1f시간",
                )
            with cond_col2:
                fatigue_level = st.select_slider(
                    "현재 피로도",
                    options=[1, 2, 3, 4, 5],
                    value=2,
                    format_func=lambda v: {1: "1 (최저)", 2: "2", 3: "3", 4: "4", 5: "5 (최고)"}[v],
                )
            condition_memo = st.text_input(
                "컨디션 메모 (선택)",
                placeholder="예: 어제 술자리가 있었어요 / 목감기 기운이 있어요",
            )

        user_condition = {
            "sleep_hours": sleep_hours,
            "fatigue_level": fatigue_level,
            "memo": condition_memo or None,
        }

        wellness = analyze_wellness(selected_models, sleep_hours=sleep_hours, fatigue_level=fatigue_level)

        # Energy timeline
        render_energy_timeline(wellness.get("energy_curve", []), selected_models)

        st.divider()

        # Wellness risk cards
        render_wellness_risks(wellness)

        st.divider()

        # AI briefing
        st.markdown("#### ✉️ 오늘의 비서 브리핑")

        has_api_key = bool(active_api_key)
        if not has_api_key:
            st.info(
                "왼쪽 사이드바에서 **Anthropic API 키**를 입력하면 "
                "Claude AI가 건강·바이오리듬·이동 경로를 종합해 자연어로 브리핑을 생성합니다.",
                icon="🔑",
            )

        btn_label = "✨ Claude 비서 브리핑 생성" if has_api_key else "📝 룰 기반 브리핑 생성"
        if st.button(btn_label, type="primary", key="secretary-btn"):
            briefing_area = st.empty()
            with st.spinner("비서가 오늘 일정을 살펴보는 중..."):
                if has_api_key:
                    full_text = ""
                    result = secretary.generate(
                        selected_models, analysis, wellness, persona,
                        user_condition=user_condition,
                        stream=True,
                    )
                    for chunk in result:
                        full_text += chunk
                        briefing_area.markdown(
                            f'<div style="border-left:4px solid #6366f1;padding:16px 20px;'
                            f'border-radius:8px;line-height:1.9;white-space:pre-wrap;">{full_text}▌</div>',
                            unsafe_allow_html=True,
                        )
                    briefing_area.markdown(
                        f'<div style="border-left:4px solid #6366f1;padding:16px 20px;'
                        f'border-radius:8px;line-height:1.9;white-space:pre-wrap;">{full_text}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    text = secretary.generate(
                        selected_models, analysis, wellness, persona,
                        user_condition=user_condition,
                        stream=False,
                    )
                    briefing_area.markdown(
                        f'<div style="border-left:4px solid #9ca3af;padding:16px 20px;'
                        f'border-radius:8px;line-height:1.9;white-space:pre-wrap;">{text}</div>',
                        unsafe_allow_html=True,
                    )


# ─── Tab 3: Schedule Analysis ─────────────────────────────────────────────────

with analysis_tab:
    st.subheader("📊 일정 분석")

    if not selected_models:
        st.info("분석할 일정을 먼저 추가해주세요.")
    else:
        briefing = generate_briefing(selected_models, analysis, persona)

        p_col, s_col = st.columns(2)
        p_col.metric("사용자 페르소나", persona["name"])
        p_col.write(persona["rationale"])
        s_col.metric("전체 일정 수", analysis["total_schedules"])
        s_col.metric("총 일정 시간", f"{analysis['total_scheduled_hours']}h")

        st.warning(briefing["risk_message"])

        st.markdown("#### 추천 액션")
        for action in briefing["recommended_actions"]:
            st.write(f"- {action}")

        with st.expander("분석 상세 데이터"):
            st.json(analysis)
