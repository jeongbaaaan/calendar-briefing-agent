from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, time
from pathlib import Path
from uuid import uuid4

import streamlit as st

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

CATEGORY_COLORS = {
    "업무": "#6366f1", "회의": "#8b5cf6", "고객": "#06b6d4",
    "운영": "#64748b", "학습": "#f59e0b", "네트워킹": "#ec4899",
    "건강": "#22c55e", "개인": "#94a3b8", "가족": "#f97316",
}

ENERGY_COLORS = {"피크": "#22c55e", "보통": "#f59e0b", "저하": "#ef4444"}

CUSTOM_CSS = """
<style>
/* Global */
[data-testid="stAppViewContainer"] { background: #f8f9fc; }
[data-testid="stMain"] { background: #f8f9fc; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: #ffffff;
    border-right: 1px solid #e8eaf0;
}

/* Metric cards */
[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #e8eaf0;
    border-radius: 12px;
    padding: 16px 20px;
}
[data-testid="stMetricLabel"] { color: #6b7280; font-size: 13px; }
[data-testid="stMetricValue"] { color: #1a1d23; font-weight: 700; }

/* Tab styling */
[data-testid="stTabs"] [role="tablist"] {
    border-bottom: 2px solid #e8eaf0;
    gap: 0;
}
[data-testid="stTabs"] button[role="tab"] {
    font-weight: 500;
    color: #6b7280;
    padding: 10px 20px;
    border-radius: 0;
    border-bottom: 2px solid transparent;
    margin-bottom: -2px;
}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    color: #6366f1;
    border-bottom: 2px solid #6366f1;
    font-weight: 600;
}

/* Form inputs */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stSelectbox"] select {
    border-radius: 8px;
    border: 1px solid #e8eaf0;
}

/* Buttons */
[data-testid="stButton"] button[kind="primary"] {
    background: #6366f1;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    padding: 10px 20px;
}
[data-testid="stButton"] button[kind="primary"]:hover {
    background: #4f46e5;
}

/* Alert boxes */
[data-testid="stAlert"] {
    border-radius: 10px;
    border: none;
}

/* Expander */
[data-testid="stExpander"] {
    border: 1px solid #e8eaf0;
    border-radius: 10px;
    background: #ffffff;
}

/* DataFrame */
[data-testid="stDataFrame"] { border-radius: 10px; }

/* Title */
h1 { font-weight: 800; color: #1a1d23; letter-spacing: -0.5px; }
h2, h3, h4 { color: #1a1d23; }
</style>
"""


# ─── Data helpers ─────────────────────────────────────────────────────────────

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


# ─── UI Components ────────────────────────────────────────────────────────────

def render_schedule_card(schedule: dict) -> None:
    cat = schedule.get("category", "기타")
    color = CATEGORY_COLORS.get(cat, "#94a3b8")
    start = schedule["start"].split(" ")[1] if " " in schedule["start"] else schedule["start"]
    end = schedule["end"].split(" ")[1] if " " in schedule["end"] else schedule["end"]

    html = f"""
    <div style="
        background:#ffffff;border:1px solid #e8eaf0;border-radius:12px;
        padding:16px 18px;margin-bottom:10px;
        border-left:4px solid {color};
        display:flex;justify-content:space-between;align-items:flex-start;
    ">
      <div style="flex:1;min-width:0;">
        <div style="font-weight:600;font-size:15px;color:#1a1d23;margin-bottom:4px;
                    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
          {schedule['title']}
        </div>
        <div style="font-size:13px;color:#6b7280;margin-bottom:6px;">
          🕐 {start} – {end} &nbsp;·&nbsp;
          <span style="background:{color}18;color:{color};padding:2px 8px;
                       border-radius:99px;font-size:12px;font-weight:500;">
            {cat}
          </span>
        </div>
        <div style="font-size:13px;color:#9ca3af;">
          📍 {schedule.get('location','미정')} &nbsp;·&nbsp; {schedule.get('notes','')[:40]}
        </div>
      </div>
    </div>
    """
    st.html(html)

    # Delete button aligned below the card
    if st.button("삭제", key=f"delete-{schedule['id']}", help="이 일정을 삭제합니다"):
        remove_schedule(str(schedule["id"]))
        st.rerun()


def render_metric_cards(selected_date: date, analysis: dict | None, persona: dict | None) -> None:
    conflict_count = len(analysis["schedule_conflicts"]) if analysis else 0
    conflict_color = "#ef4444" if conflict_count else "#22c55e"
    conflict_label = f"⚠️ {conflict_count}건" if conflict_count else "✅ 없음"

    html = f"""
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px;">
      <div style="background:#fff;border:1px solid #e8eaf0;border-radius:12px;padding:16px 20px;">
        <div style="font-size:12px;color:#9ca3af;margin-bottom:4px;font-weight:500;text-transform:uppercase;letter-spacing:.5px;">날짜</div>
        <div style="font-size:22px;font-weight:700;color:#1a1d23;">{selected_date.strftime('%m/%d')}</div>
        <div style="font-size:12px;color:#9ca3af;">{selected_date.strftime('%A')}</div>
      </div>
      <div style="background:#fff;border:1px solid #e8eaf0;border-radius:12px;padding:16px 20px;">
        <div style="font-size:12px;color:#9ca3af;margin-bottom:4px;font-weight:500;text-transform:uppercase;letter-spacing:.5px;">일정 수</div>
        <div style="font-size:22px;font-weight:700;color:#6366f1;">{analysis['total_schedules'] if analysis else 0}개</div>
        <div style="font-size:12px;color:#9ca3af;">오늘 총 일정</div>
      </div>
      <div style="background:#fff;border:1px solid #e8eaf0;border-radius:12px;padding:16px 20px;">
        <div style="font-size:12px;color:#9ca3af;margin-bottom:4px;font-weight:500;text-transform:uppercase;letter-spacing:.5px;">총 시간</div>
        <div style="font-size:22px;font-weight:700;color:#1a1d23;">{analysis['total_scheduled_hours'] if analysis else 0}h</div>
        <div style="font-size:12px;color:#9ca3af;">스케줄된 시간</div>
      </div>
      <div style="background:#fff;border:1px solid #e8eaf0;border-radius:12px;padding:16px 20px;">
        <div style="font-size:12px;color:#9ca3af;margin-bottom:4px;font-weight:500;text-transform:uppercase;letter-spacing:.5px;">충돌</div>
        <div style="font-size:22px;font-weight:700;color:{conflict_color};">{conflict_label}</div>
        <div style="font-size:12px;color:#9ca3af;">{persona['name'] if persona else '일정 없음'}</div>
      </div>
    </div>
    """
    st.html(html)


def render_energy_timeline(energy_curve: list[dict], schedules: list) -> None:
    if not energy_curve:
        return

    day_start, day_end = 7.0, 22.0
    span = day_end - day_start

    bg_bars = ""
    for w in energy_curve:
        hs = max(w["hour_start"], day_start)
        he = min(w["hour_end"], day_end)
        if he <= hs:
            continue
        l = (hs - day_start) / span * 100
        ww = (he - hs) / span * 100
        c = ENERGY_COLORS.get(w["label"], "#9ca3af")
        op = 0.18 if w["label"] == "저하" else 0.10
        label = w["label"]
        desc = w["description"]
        bg_bars += (
            f'<div style="position:absolute;left:{l:.2f}%;width:{ww:.2f}%;height:100%;'
            f'background:{c};opacity:{op};border-radius:4px;" title="{label}: {desc}"></div>'
        )

    evt_bars = ""
    for s in schedules:
        hs = s.start.hour + s.start.minute / 60
        he = s.end.hour + s.end.minute / 60
        l = max(0, (hs - day_start) / span * 100)
        ww = max(0.8, (he - hs) / span * 100)
        cat = getattr(s, "category", "기타")
        c = CATEGORY_COLORS.get(cat, "#6366f1")
        title = s.title
        evt_bars += (
            f'<div style="position:absolute;left:{l:.2f}%;width:{ww:.2f}%;height:100%;'
            f'background:{c};opacity:0.85;border-radius:3px;" title="{title}"></div>'
        )

    hour_ticks = "".join(
        f'<span style="position:absolute;left:{(h - day_start) / span * 100:.1f}%;'
        f'font-size:11px;color:#9ca3af;transform:translateX(-50%);">{h}시</span>'
        for h in range(int(day_start), int(day_end) + 1, 2)
    )

    legend_items = "".join(
        f'<span style="display:inline-flex;align-items:center;gap:5px;margin-right:14px;font-size:12px;color:#6b7280;">'
        f'<span style="width:10px;height:10px;background:{c};border-radius:2px;display:inline-block;opacity:0.8;"></span>'
        f'{lbl}</span>'
        for lbl, c in ENERGY_COLORS.items()
    ) + (
        '<span style="display:inline-flex;align-items:center;gap:5px;font-size:12px;color:#6b7280;">'
        '<span style="width:10px;height:10px;background:#6366f1;border-radius:2px;display:inline-block;opacity:0.85;"></span>'
        '내 일정</span>'
    )

    html = f"""
    <div style="background:#fff;border:1px solid #e8eaf0;border-radius:12px;padding:20px 24px;margin-bottom:16px;">
      <div style="font-size:14px;font-weight:600;color:#1a1d23;margin-bottom:12px;">⚡ 오늘의 에너지 흐름</div>
      <div style="margin-bottom:10px;">{legend_items}</div>
      <div style="position:relative;height:28px;background:#f1f5f9;border-radius:6px;overflow:hidden;margin-bottom:6px;">
        {bg_bars}{evt_bars}
      </div>
      <div style="position:relative;height:18px;">{hour_ticks}</div>
    </div>
    """
    st.html(html)


def render_wellness_panel(wellness: dict) -> None:
    fatigue = wellness.get("fatigue_risks", [])
    meals = wellness.get("meal_risks", [])
    travel = wellness.get("travel_risks", [])
    bio = wellness.get("biorhythm_mismatches", [])

    items = (
        [("🔴", r["description"], "#fef2f2", "#ef4444") for r in fatigue]
        + [("🍽️", r["description"], "#fffbeb", "#f59e0b") for r in meals]
        + [("🚶", r["description"], "#eff6ff", "#3b82f6") for r in travel]
        + [("⚡", m, "#fef3c7", "#d97706") for m in bio]
    )

    if not wellness.get("has_movement"):
        items.append(("🏃", "오늘 운동/신체 활동 일정이 없습니다. 점심 후 10분 산책을 추천드려요.", "#f0fdf4", "#22c55e"))
    if wellness.get("screen_heavy"):
        items.append(("👁️", "화면 기반 일정이 많습니다. 20분마다 20초씩 먼 곳을 바라보세요.", "#f0f9ff", "#0ea5e9"))

    if not items:
        st.html("""
        <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;padding:14px 18px;color:#15803d;font-size:14px;">
          ✅ 오늘 건강·컨디션 리스크가 발견되지 않았습니다.
        </div>
        """)
        return

    cards = "".join(
        f'<div style="background:{bg};border:1px solid {bc}30;border-radius:10px;'
        f'padding:12px 16px;margin-bottom:8px;font-size:14px;color:#1a1d23;line-height:1.5;">'
        f'<span style="margin-right:8px;">{icon}</span>{desc}</div>'
        for icon, desc, bg, bc in items
    )

    st.html(f'<div style="margin-bottom:4px;">{cards}</div>')


# ─── Main ─────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="캘린더 브리핑 에이전트", layout="wide", page_icon="📅")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
initialize_state()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div style="font-size:22px;font-weight:800;color:#1a1d23;margin-bottom:4px;">📅 브리핑</div>'
        '<div style="font-size:12px;color:#9ca3af;margin-bottom:20px;">AI 개인 비서 에이전트</div>',
        unsafe_allow_html=True,
    )

    env_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if env_key:
        st.markdown(
            '<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;'
            'padding:10px 14px;font-size:13px;color:#15803d;">✅ Claude API 연결됨</div>',
            unsafe_allow_html=True,
        )
        active_api_key = env_key
    else:
        st.markdown('<div style="font-size:13px;font-weight:600;color:#374151;margin-bottom:6px;">Claude API 키</div>', unsafe_allow_html=True)
        input_key = st.text_input(
            "API 키", label_visibility="collapsed",
            type="password", placeholder="sk-ant-...",
            help="https://console.anthropic.com 에서 발급",
        )
        if input_key.strip():
            os.environ["ANTHROPIC_API_KEY"] = input_key.strip()
            active_api_key = input_key.strip()
            st.markdown(
                '<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;'
                'padding:10px 14px;font-size:13px;color:#15803d;">✅ API 키 적용됨</div>',
                unsafe_allow_html=True,
            )
        else:
            active_api_key = ""
            st.markdown(
                '<div style="background:#fef3c7;border:1px solid #fde68a;border-radius:8px;'
                'padding:10px 14px;font-size:13px;color:#92400e;">'
                '🔑 API 키를 입력하면<br>Claude 브리핑이 활성화됩니다.</div>',
                unsafe_allow_html=True,
            )

    st.divider()

    st.markdown('<div style="font-size:12px;color:#9ca3af;margin-bottom:8px;">모델</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:13px;font-weight:500;color:#374151;">claude-sonnet-4-6</div>', unsafe_allow_html=True)

    st.markdown('<br>', unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:12px;color:#9ca3af;line-height:1.6;">'
        '🤖 AI 비서 브리핑 탭에서<br>브리핑을 생성하세요.</div>',
        unsafe_allow_html=True,
    )


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    '<h1 style="font-size:28px;font-weight:800;color:#1a1d23;margin-bottom:2px;">📅 캘린더 브리핑 에이전트</h1>'
    '<p style="font-size:14px;color:#9ca3af;margin-bottom:20px;">'
    'AI 개인 비서가 건강·컨디션·바이오리듬·이동 경로를 챙겨드립니다.</p>',
    unsafe_allow_html=True,
)

date_col, _ = st.columns([1, 3])
with date_col:
    selected_date = st.date_input("브리핑 날짜", value=st.session_state.schedule_date, label_visibility="collapsed")
st.session_state.schedule_date = selected_date

selected_items = schedules_for_date(st.session_state.schedule_items, selected_date)
selected_models = get_schedule_models(selected_items)
selected_rows = get_schedule_rows(selected_items)

analysis = analyze_schedule(selected_models) if selected_models else None
persona = classify_persona(analysis) if analysis else None

render_metric_cards(selected_date, analysis, persona)

calendar_tab, secretary_tab, analysis_tab = st.tabs(["📆 캘린더", "🤖 AI 비서 브리핑", "📊 일정 분석"])


# ─── Tab 1: Calendar ─────────────────────────────────────────────────────────

with calendar_tab:
    input_col, list_col = st.columns([1, 1.4], gap="large")

    with input_col:
        st.markdown('<div style="font-size:16px;font-weight:700;color:#1a1d23;margin-bottom:12px;">일정 추가</div>', unsafe_allow_html=True)
        with st.form("schedule-form", clear_on_submit=True):
            title = st.text_input("일정명", placeholder="예: 고객 인터뷰")
            col_a, col_b = st.columns(2)
            with col_a:
                category = st.selectbox("카테고리", CATEGORY_OPTIONS)
            with col_b:
                location = st.text_input("장소", placeholder="예: 강남역 / 줌")
            col_c, col_d = st.columns(2)
            with col_c:
                start_time = st.time_input("시작", value=time(9, 0), step=900)
            with col_d:
                end_time = st.time_input("종료", value=time(10, 0), step=900)
            notes = st.text_area("메모", placeholder="준비 사항이나 확인할 내용을 적어주세요.", height=80)
            submitted = st.form_submit_button("＋ 일정 추가하기", type="primary", use_container_width=True)

        if submitted:
            ok, msg = add_schedule(title, category, selected_date, start_time, end_time, location, notes)
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

        if st.button("💾 현재 일정 저장", use_container_width=True):
            persist_current_data()
            st.success("저장 완료.")

    with list_col:
        st.markdown(
            f'<div style="font-size:16px;font-weight:700;color:#1a1d23;margin-bottom:12px;">'
            f'일정 목록 <span style="font-size:13px;font-weight:400;color:#9ca3af;">'
            f'{len(selected_rows)}개</span></div>',
            unsafe_allow_html=True,
        )
        if not selected_rows:
            st.html(
                '<div style="background:#f8f9fc;border:1.5px dashed #e8eaf0;border-radius:12px;'
                'padding:32px;text-align:center;color:#9ca3af;font-size:14px;">'
                '📭 선택한 날짜에 일정이 없습니다.<br>왼쪽에서 새 일정을 추가해보세요.</div>'
            )
        else:
            for schedule in selected_rows:
                render_schedule_card(schedule)

            with st.expander("📋 표로 보기"):
                st.dataframe(
                    selected_rows,
                    hide_index=True,
                    column_order=["title", "category", "start", "end", "duration_hours", "location"],
                    column_config={
                        "title": "일정명", "category": "카테고리",
                        "start": "시작", "end": "종료",
                        "duration_hours": st.column_config.NumberColumn("시간", format="%.1fh"),
                        "location": "장소",
                    },
                )


# ─── Tab 2: AI Secretary ─────────────────────────────────────────────────────

with secretary_tab:
    st.markdown(
        '<div style="font-size:16px;font-weight:700;color:#1a1d23;margin-bottom:4px;">🤖 AI 개인 비서 브리핑</div>'
        '<div style="font-size:13px;color:#9ca3af;margin-bottom:16px;">'
        '오늘 컨디션을 입력하면 건강·바이오리듬·이동 경로까지 종합해서 챙겨드립니다.</div>',
        unsafe_allow_html=True,
    )

    if not selected_models:
        st.html(
            '<div style="background:#f8f9fc;border:1.5px dashed #e8eaf0;border-radius:12px;'
            'padding:40px;text-align:center;color:#9ca3af;font-size:14px;">'
            '📭 브리핑을 받으려면 먼저 일정을 추가해주세요.</div>'
        )
    else:
        # Condition input
        st.html('<div style="font-size:14px;font-weight:600;color:#374151;margin-bottom:8px;">오늘 컨디션</div>')
        with st.container(border=True):
            cond_col1, cond_col2 = st.columns(2)
            with cond_col1:
                sleep_hours = st.slider(
                    "어젯밤 수면 시간", min_value=3.0, max_value=10.0,
                    value=7.0, step=0.5, format="%.1f시간",
                )
            with cond_col2:
                fatigue_level = st.select_slider(
                    "현재 피로도", options=[1, 2, 3, 4, 5], value=2,
                    format_func=lambda v: {1: "😊 매우 좋음", 2: "🙂 좋음", 3: "😐 보통", 4: "😔 피곤", 5: "😩 매우 피곤"}[v],
                )
            condition_memo = st.text_input(
                "컨디션 메모 (선택)",
                placeholder="예: 어젯밤 술자리가 있었어요 / 목감기 기운이 있어요",
            )

        user_condition = {
            "sleep_hours": sleep_hours,
            "fatigue_level": fatigue_level,
            "memo": condition_memo or None,
        }

        wellness = analyze_wellness(selected_models, sleep_hours=sleep_hours, fatigue_level=fatigue_level)

        st.markdown("")
        render_energy_timeline(wellness.get("energy_curve", []), selected_models)

        st.html('<div style="font-size:14px;font-weight:600;color:#374151;margin-bottom:8px;">건강·컨디션 리스크</div>')
        render_wellness_panel(wellness)

        st.markdown("")
        st.html('<div style="font-size:14px;font-weight:600;color:#374151;margin-bottom:4px;">✉️ 비서 브리핑</div>')

        has_api_key = bool(active_api_key)
        if not has_api_key:
            st.html(
                '<div style="background:#fef3c7;border:1px solid #fde68a;border-radius:10px;'
                'padding:14px 18px;font-size:13px;color:#92400e;margin-bottom:12px;">'
                '🔑 사이드바에서 <b>Anthropic API 키</b>를 입력하면 Claude AI가 자연어로 브리핑을 생성합니다.<br>'
                '<span style="font-size:12px;color:#b45309;">API 키 없이는 룰 기반 브리핑이 생성됩니다.</span></div>'
            )

        btn_label = "✨ Claude 비서 브리핑 생성하기" if has_api_key else "📝 브리핑 생성하기"
        if st.button(btn_label, type="primary", key="secretary-btn", use_container_width=True):
            briefing_area = st.empty()
            with st.spinner("비서가 오늘 일정을 살펴보는 중..."):
                if has_api_key:
                    full_text = ""
                    for chunk in secretary.generate(
                        selected_models, analysis, wellness, persona,
                        user_condition=user_condition, stream=True,
                    ):
                        full_text += chunk
                        briefing_area.markdown(
                            f'<div style="background:#fafafe;border:1px solid #e0e3f0;'
                            f'border-left:4px solid #6366f1;border-radius:10px;'
                            f'padding:20px 24px;line-height:1.9;font-size:14px;color:#1a1d23;">'
                            f'{full_text}▌</div>',
                            unsafe_allow_html=True,
                        )
                    briefing_area.markdown(
                        f'<div style="background:#fafafe;border:1px solid #e0e3f0;'
                        f'border-left:4px solid #6366f1;border-radius:10px;'
                        f'padding:20px 24px;line-height:1.9;font-size:14px;color:#1a1d23;">'
                        f'{full_text}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    text = secretary.generate(
                        selected_models, analysis, wellness, persona,
                        user_condition=user_condition, stream=False,
                    )
                    briefing_area.markdown(
                        f'<div style="background:#f8f9fc;border:1px solid #e8eaf0;'
                        f'border-left:4px solid #9ca3af;border-radius:10px;'
                        f'padding:20px 24px;line-height:1.9;font-size:14px;color:#374151;">'
                        f'{text}</div>',
                        unsafe_allow_html=True,
                    )


# ─── Tab 3: Analysis ─────────────────────────────────────────────────────────

with analysis_tab:
    st.markdown('<div style="font-size:16px;font-weight:700;color:#1a1d23;margin-bottom:16px;">📊 일정 분석</div>', unsafe_allow_html=True)

    if not selected_models:
        st.html(
            '<div style="background:#f8f9fc;border:1.5px dashed #e8eaf0;border-radius:12px;'
            'padding:40px;text-align:center;color:#9ca3af;font-size:14px;">'
            '📭 분석할 일정을 먼저 추가해주세요.</div>'
        )
    else:
        briefing = generate_briefing(selected_models, analysis, persona)

        # Persona card
        p_color = CATEGORY_COLORS.get("업무", "#6366f1")
        st.html(f"""
        <div style="background:#fff;border:1px solid #e8eaf0;border-radius:12px;padding:20px 24px;margin-bottom:16px;
                    border-top:4px solid {p_color};">
          <div style="font-size:12px;color:#9ca3af;font-weight:500;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;">오늘의 유형</div>
          <div style="font-size:20px;font-weight:700;color:#1a1d23;margin-bottom:6px;">{persona['name']}</div>
          <div style="font-size:13px;color:#6b7280;line-height:1.6;">{persona['rationale']}</div>
        </div>
        """)

        # Risk message
        if analysis["schedule_conflicts"] or analysis["insufficient_buffer_time"]:
            st.warning(briefing["risk_message"])
        else:
            st.success(briefing["risk_message"])

        # Recommended actions
        st.html('<div style="font-size:14px;font-weight:600;color:#374151;margin:16px 0 8px;">추천 액션</div>')
        actions_html = "".join(
            f'<div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:8px;">'
            f'<span style="color:#6366f1;font-size:16px;flex-shrink:0;">→</span>'
            f'<span style="font-size:14px;color:#374151;line-height:1.6;">{action}</span></div>'
            for action in briefing["recommended_actions"]
        )
        st.html(f'<div style="background:#fff;border:1px solid #e8eaf0;border-radius:12px;padding:20px 24px;">{actions_html}</div>')

        # Category distribution
        if analysis["category_distribution"]:
            st.html('<div style="font-size:14px;font-weight:600;color:#374151;margin:16px 0 8px;">카테고리 분포</div>')
            total = sum(analysis["category_distribution"].values())
            dist_bars = ""
            for cat, count in sorted(analysis["category_distribution"].items(), key=lambda x: -x[1]):
                pct = count / total * 100
                c = CATEGORY_COLORS.get(cat, "#94a3b8")
                dist_bars += (
                    f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">'
                    f'<span style="width:64px;font-size:13px;color:#6b7280;text-align:right;">{cat}</span>'
                    f'<div style="flex:1;height:8px;background:#f1f5f9;border-radius:99px;overflow:hidden;">'
                    f'<div style="width:{pct:.0f}%;height:100%;background:{c};border-radius:99px;"></div></div>'
                    f'<span style="font-size:12px;color:#9ca3af;width:28px;">{count}개</span>'
                    f'</div>'
                )
            st.html(f'<div style="background:#fff;border:1px solid #e8eaf0;border-radius:12px;padding:20px 24px;">{dist_bars}</div>')

        with st.expander("🔍 분석 원본 데이터"):
            st.json(analysis)
