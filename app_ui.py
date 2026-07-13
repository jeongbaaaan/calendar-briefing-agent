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
import google_calendar as gcal


CATEGORY_OPTIONS = ["업무", "회의", "고객", "운영", "학습", "네트워킹", "건강", "개인", "가족"]

CATEGORY_COLORS = {
    "업무": "#6366f1", "회의": "#8b5cf6", "고객": "#06b6d4",
    "운영": "#64748b", "학습": "#f59e0b", "네트워킹": "#ec4899",
    "건강": "#22c55e", "개인": "#94a3b8", "가족": "#f97316",
}

ENERGY_COLORS = {"피크": "#22c55e", "보통": "#f59e0b", "저하": "#ef4444"}

CUSTOM_CSS = """
<style>
[data-testid="stAppViewContainer"] { background: #f8f9fc; }
[data-testid="stMain"] { background: #f8f9fc; }
[data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid #e8eaf0; }

[data-testid="stMetric"] {
    background: #ffffff; border: 1px solid #e8eaf0;
    border-radius: 12px; padding: 16px 20px;
}
[data-testid="stMetricLabel"] { color: #6b7280; font-size: 13px; }
[data-testid="stMetricValue"] { color: #1a1d23; font-weight: 700; }

[data-testid="stTabs"] [role="tablist"] { border-bottom: 2px solid #e8eaf0; gap: 0; }
[data-testid="stTabs"] button[role="tab"] {
    font-weight: 500; color: #6b7280; padding: 10px 20px;
    border-radius: 0; border-bottom: 2px solid transparent; margin-bottom: -2px;
}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    color: #6366f1; border-bottom: 2px solid #6366f1; font-weight: 600;
}

[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    border-radius: 8px; border: 1px solid #e8eaf0;
}

[data-testid="stButton"] button[kind="primary"] {
    background: #6366f1; border: none; border-radius: 8px;
    font-weight: 600; padding: 10px 20px;
}
[data-testid="stButton"] button[kind="primary"]:hover { background: #4f46e5; }

[data-testid="stAlert"] { border-radius: 10px; border: none; }
[data-testid="stExpander"] {
    border: 1px solid #e8eaf0; border-radius: 10px; background: #ffffff;
}
h1, h2, h3, h4 { color: #1a1d23; }
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
    if "gcal_token" not in st.session_state:
        st.session_state.gcal_token = gcal.load_saved_token()
    if "gcal_flow" not in st.session_state:
        st.session_state.gcal_flow = None
    if "gcal_calendars" not in st.session_state:
        st.session_state.gcal_calendars = []


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
    notes_preview = str(schedule.get("notes", ""))[:45]

    st.html(f"""
    <div style="background:#fff;border:1px solid #e8eaf0;border-radius:12px;
                padding:16px 18px;margin-bottom:10px;border-left:4px solid {color};">
      <div style="font-weight:600;font-size:15px;color:#1a1d23;margin-bottom:4px;">
        {schedule['title']}
      </div>
      <div style="font-size:13px;color:#6b7280;margin-bottom:6px;">
        🕐 {start} – {end} &nbsp;·&nbsp;
        <span style="background:{color}18;color:{color};padding:2px 8px;
                     border-radius:99px;font-size:12px;font-weight:500;">{cat}</span>
      </div>
      <div style="font-size:13px;color:#9ca3af;">
        📍 {schedule.get('location','미정')}{' · ' + notes_preview if notes_preview and notes_preview != '메모 없음' else ''}
      </div>
    </div>
    """)
    if st.button("삭제", key=f"delete-{schedule['id']}", help="이 일정 삭제"):
        remove_schedule(str(schedule["id"]))
        st.rerun()


def render_metric_cards(selected_date: date, analysis: dict | None, persona: dict | None) -> None:
    conflict_count = len(analysis["schedule_conflicts"]) if analysis else 0
    conflict_color = "#ef4444" if conflict_count else "#22c55e"
    conflict_label = f"⚠️ {conflict_count}건" if conflict_count else "✅ 없음"
    gcal_badge = (
        '<span style="font-size:11px;background:#dcfce7;color:#16a34a;'
        'padding:2px 7px;border-radius:99px;font-weight:500;">Google 연동</span>'
        if st.session_state.gcal_token else ""
    )

    st.html(f"""
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px;">
      <div style="background:#fff;border:1px solid #e8eaf0;border-radius:12px;padding:16px 20px;">
        <div style="font-size:11px;color:#9ca3af;margin-bottom:4px;font-weight:500;
                    text-transform:uppercase;letter-spacing:.5px;">날짜</div>
        <div style="font-size:22px;font-weight:700;color:#1a1d23;">{selected_date.strftime('%m/%d')}</div>
        <div style="font-size:12px;color:#9ca3af;">{selected_date.strftime('%A')} {gcal_badge}</div>
      </div>
      <div style="background:#fff;border:1px solid #e8eaf0;border-radius:12px;padding:16px 20px;">
        <div style="font-size:11px;color:#9ca3af;margin-bottom:4px;font-weight:500;
                    text-transform:uppercase;letter-spacing:.5px;">일정 수</div>
        <div style="font-size:22px;font-weight:700;color:#6366f1;">{analysis['total_schedules'] if analysis else 0}개</div>
        <div style="font-size:12px;color:#9ca3af;">오늘 총 일정</div>
      </div>
      <div style="background:#fff;border:1px solid #e8eaf0;border-radius:12px;padding:16px 20px;">
        <div style="font-size:11px;color:#9ca3af;margin-bottom:4px;font-weight:500;
                    text-transform:uppercase;letter-spacing:.5px;">총 시간</div>
        <div style="font-size:22px;font-weight:700;color:#1a1d23;">{analysis['total_scheduled_hours'] if analysis else 0}h</div>
        <div style="font-size:12px;color:#9ca3af;">스케줄된 시간</div>
      </div>
      <div style="background:#fff;border:1px solid #e8eaf0;border-radius:12px;padding:16px 20px;">
        <div style="font-size:11px;color:#9ca3af;margin-bottom:4px;font-weight:500;
                    text-transform:uppercase;letter-spacing:.5px;">충돌</div>
        <div style="font-size:22px;font-weight:700;color:{conflict_color};">{conflict_label}</div>
        <div style="font-size:12px;color:#9ca3af;">{persona['name'] if persona else '일정 없음'}</div>
      </div>
    </div>
    """)


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
        label, desc = w["label"], w["description"]
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
        c = CATEGORY_COLORS.get(getattr(s, "category", ""), "#6366f1")
        evt_bars += (
            f'<div style="position:absolute;left:{l:.2f}%;width:{ww:.2f}%;height:100%;'
            f'background:{c};opacity:0.85;border-radius:3px;" title="{s.title}"></div>'
        )

    ticks = "".join(
        f'<span style="position:absolute;left:{(h - day_start) / span * 100:.1f}%;'
        f'font-size:11px;color:#9ca3af;transform:translateX(-50%);">{h}시</span>'
        for h in range(int(day_start), int(day_end) + 1, 2)
    )

    legend = "".join(
        f'<span style="display:inline-flex;align-items:center;gap:5px;margin-right:14px;font-size:12px;color:#6b7280;">'
        f'<span style="width:10px;height:10px;background:{c};border-radius:2px;display:inline-block;opacity:.8;"></span>'
        f'{lbl}</span>'
        for lbl, c in ENERGY_COLORS.items()
    ) + (
        '<span style="display:inline-flex;align-items:center;gap:5px;font-size:12px;color:#6b7280;">'
        '<span style="width:10px;height:10px;background:#6366f1;border-radius:2px;display:inline-block;opacity:.85;"></span>'
        '내 일정</span>'
    )

    st.html(f"""
    <div style="background:#fff;border:1px solid #e8eaf0;border-radius:12px;padding:20px 24px;margin-bottom:16px;">
      <div style="font-size:14px;font-weight:600;color:#1a1d23;margin-bottom:12px;">⚡ 오늘의 에너지 흐름</div>
      <div style="margin-bottom:10px;">{legend}</div>
      <div style="position:relative;height:28px;background:#f1f5f9;border-radius:6px;overflow:hidden;margin-bottom:6px;">
        {bg_bars}{evt_bars}
      </div>
      <div style="position:relative;height:18px;">{ticks}</div>
    </div>
    """)


def render_wellness_panel(wellness: dict) -> None:
    items = (
        [("🔴", r["description"], "#fef2f2", "#ef4444") for r in wellness.get("fatigue_risks", [])]
        + [("🍽️", r["description"], "#fffbeb", "#f59e0b") for r in wellness.get("meal_risks", [])]
        + [("🚶", r["description"], "#eff6ff", "#3b82f6") for r in wellness.get("travel_risks", [])]
        + [("⚡", m, "#fef3c7", "#d97706") for m in wellness.get("biorhythm_mismatches", [])]
    )
    if not wellness.get("has_movement"):
        items.append(("🏃", "오늘 운동/신체 활동 일정이 없습니다. 점심 후 10분 산책을 추천드려요.", "#f0fdf4", "#22c55e"))
    if wellness.get("screen_heavy"):
        items.append(("👁️", "화면 기반 일정이 많습니다. 20분마다 20초씩 먼 곳을 바라보세요.", "#f0f9ff", "#0ea5e9"))

    if not items:
        st.html('<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;'
                'padding:14px 18px;color:#15803d;font-size:14px;">✅ 건강·컨디션 리스크가 발견되지 않았습니다.</div>')
        return

    cards = "".join(
        f'<div style="background:{bg};border:1px solid {bc}30;border-radius:10px;'
        f'padding:12px 16px;margin-bottom:8px;font-size:14px;color:#1a1d23;line-height:1.5;">'
        f'<span style="margin-right:8px;">{icon}</span>{desc}</div>'
        for icon, desc, bg, bc in items
    )
    st.html(f'<div style="margin-bottom:4px;">{cards}</div>')


# ─── Sidebar: Google Calendar connection ──────────────────────────────────────

def render_gcal_sidebar(selected_date: date) -> None:
    st.markdown(
        '<div style="font-size:13px;font-weight:600;color:#374151;margin-bottom:8px;">📅 Google Calendar</div>',
        unsafe_allow_html=True,
    )

    token = st.session_state.gcal_token

    if token:
        st.html(
            '<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;'
            'padding:10px 14px;font-size:13px;color:#15803d;margin-bottom:10px;">✅ 연결됨</div>'
        )

        # Calendar selector
        if not st.session_state.gcal_calendars:
            try:
                st.session_state.gcal_calendars = gcal.list_calendars(token)
            except Exception:
                st.session_state.gcal_token = None
                gcal.delete_saved_token()
                st.rerun()

        if st.session_state.gcal_calendars:
            cal_options = {c["name"]: c["id"] for c in st.session_state.gcal_calendars}
            selected_cal_name = st.selectbox(
                "캘린더 선택", list(cal_options.keys()), label_visibility="collapsed"
            )
            selected_cal_id = cal_options[selected_cal_name]

            if st.button("📥 오늘 일정 가져오기", use_container_width=True):
                with st.spinner("Google Calendar에서 가져오는 중..."):
                    try:
                        imported = gcal.fetch_events(token, selected_cal_id, selected_date)
                        if not imported:
                            st.info("해당 날짜에 일정이 없습니다.")
                        else:
                            # Merge: remove existing gcal- items, add new ones
                            st.session_state.schedule_items = [
                                item for item in st.session_state.schedule_items
                                if not str(item.get("id", "")).startswith("gcal-")
                            ]
                            for s in imported:
                                st.session_state.schedule_items.append({
                                    "id": s.id,
                                    "title": s.title,
                                    "category": s.category,
                                    "start": s.start.strftime(DATETIME_FORMAT),
                                    "end": s.end.strftime(DATETIME_FORMAT),
                                    "location": s.location or "미정",
                                    "notes": s.notes or "Google Calendar에서 가져온 일정",
                                })
                            st.success(f"{len(imported)}개 일정을 가져왔습니다.")
                            st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")

        if st.button("연결 해제", use_container_width=True):
            gcal.delete_saved_token()
            st.session_state.gcal_token = None
            st.session_state.gcal_calendars = []
            st.rerun()

    else:
        # Step 1: Upload credentials.json
        creds_file = st.file_uploader(
            "credentials.json 업로드",
            type=["json"],
            help="Google Cloud Console → OAuth 2.0 클라이언트 → 데스크톱 앱으로 생성한 credentials.json",
            label_visibility="collapsed",
        )

        if creds_file:
            if "gcal_creds_json" not in st.session_state:
                st.session_state.gcal_creds_json = creds_file.read().decode()
                try:
                    flow, auth_url = gcal.get_auth_url(st.session_state.gcal_creds_json)
                    st.session_state.gcal_flow = flow
                    st.session_state.gcal_auth_url = auth_url
                except Exception as e:
                    st.error(f"credentials.json 오류: {e}")
                    del st.session_state.gcal_creds_json

        if st.session_state.get("gcal_auth_url"):
            st.markdown(
                f'<a href="{st.session_state.gcal_auth_url}" target="_blank">'
                f'<div style="background:#4285f4;color:#fff;border-radius:8px;'
                f'padding:9px 14px;font-size:13px;font-weight:600;text-align:center;'
                f'text-decoration:none;margin-bottom:10px;">🔗 Google 계정 연결하기</div></a>',
                unsafe_allow_html=True,
            )
            code_input = st.text_input(
                "인증 코드 붙여넣기",
                placeholder="Google에서 받은 코드",
                label_visibility="collapsed",
            )
            if st.button("연결 완료", type="primary", use_container_width=True):
                if code_input.strip():
                    try:
                        token = gcal.exchange_code(st.session_state.gcal_flow, code_input)
                        st.session_state.gcal_token = token
                        st.session_state.gcal_flow = None
                        st.session_state.pop("gcal_auth_url", None)
                        st.session_state.pop("gcal_creds_json", None)
                        st.success("연결 완료!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"인증 실패: {e}")
                else:
                    st.warning("코드를 입력해주세요.")
        elif not creds_file:
            st.html(
                '<div style="background:#f8f9fc;border:1.5px dashed #e8eaf0;border-radius:8px;'
                'padding:12px 14px;font-size:12px;color:#9ca3af;line-height:1.6;">'
                'credentials.json을 업로드하면<br>Google 캘린더를 자동으로<br>불러올 수 있습니다.'
                '</div>'
            )


# ─── Main ─────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="Briefly", layout="wide", page_icon="✦")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
initialize_state()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.html("""
    <div style="padding:4px 0 20px;">
      <div style="font-size:24px;font-weight:900;color:#1a1d23;letter-spacing:-1px;">Briefly</div>
      <div style="font-size:12px;color:#9ca3af;margin-top:2px;">AI 개인 비서 에이전트</div>
    </div>
    """)

    # Google Calendar section
    render_gcal_sidebar(
        st.session_state.get("schedule_date", datetime.today().date())
    )

    st.divider()

    # Claude API section
    st.html('<div style="font-size:13px;font-weight:600;color:#374151;margin-bottom:8px;">🤖 Claude AI</div>')
    env_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if env_key:
        st.html('<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;'
                'padding:10px 14px;font-size:13px;color:#15803d;">✅ API 연결됨</div>')
        active_api_key = env_key
    else:
        input_key = st.text_input(
            "Anthropic API 키", label_visibility="collapsed",
            type="password", placeholder="sk-ant-...",
            help="https://console.anthropic.com",
        )
        if input_key.strip():
            os.environ["ANTHROPIC_API_KEY"] = input_key.strip()
            active_api_key = input_key.strip()
            st.html('<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;'
                    'padding:10px 14px;font-size:13px;color:#15803d;">✅ API 키 적용됨</div>')
        else:
            active_api_key = ""
            st.html('<div style="background:#fef3c7;border:1px solid #fde68a;border-radius:8px;'
                    'padding:10px 14px;font-size:13px;color:#92400e;">'
                    '🔑 API 키를 입력하면<br>Claude 브리핑이 활성화됩니다.</div>')

    st.html('<div style="margin-top:10px;font-size:11px;color:#d1d5db;">claude-sonnet-4-6</div>')


# ── Header ────────────────────────────────────────────────────────────────────
st.html("""
<div style="margin-bottom:20px;">
  <div style="font-size:32px;font-weight:900;color:#1a1d23;letter-spacing:-1.5px;line-height:1;">
    Briefly
  </div>
  <div style="font-size:14px;color:#9ca3af;margin-top:4px;">
    당신의 하루를 먼저 챙기는 AI 개인 비서
  </div>
</div>
""")

date_col, _ = st.columns([1, 3])
with date_col:
    selected_date = st.date_input(
        "날짜", value=st.session_state.schedule_date, label_visibility="collapsed"
    )
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
        st.html('<div style="font-size:16px;font-weight:700;color:#1a1d23;margin-bottom:12px;">일정 추가</div>')
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
            st.success(msg) if ok else st.error(msg)
            if ok:
                st.rerun()

        if st.button("💾 현재 일정 저장", use_container_width=True):
            persist_current_data()
            st.success("저장 완료.")

    with list_col:
        gcal_badge = " 🔗" if st.session_state.gcal_token else ""
        st.html(
            f'<div style="font-size:16px;font-weight:700;color:#1a1d23;margin-bottom:12px;">'
            f'일정 목록{gcal_badge} <span style="font-size:13px;font-weight:400;color:#9ca3af;">'
            f'{len(selected_rows)}개</span></div>'
        )
        if not selected_rows:
            st.html(
                '<div style="background:#f8f9fc;border:1.5px dashed #e8eaf0;border-radius:12px;'
                'padding:40px;text-align:center;color:#9ca3af;font-size:14px;">'
                '📭 선택한 날짜에 일정이 없습니다.<br>'
                '직접 추가하거나, 사이드바에서 Google Calendar를 연동하세요.</div>'
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
    st.html(
        '<div style="font-size:16px;font-weight:700;color:#1a1d23;margin-bottom:4px;">🤖 AI 개인 비서 브리핑</div>'
        '<div style="font-size:13px;color:#9ca3af;margin-bottom:16px;">'
        '컨디션을 입력하면 건강·바이오리듬·이동 경로까지 종합해서 챙겨드립니다.</div>'
    )

    if not selected_models:
        st.html(
            '<div style="background:#f8f9fc;border:1.5px dashed #e8eaf0;border-radius:12px;'
            'padding:40px;text-align:center;color:#9ca3af;font-size:14px;">'
            '📭 브리핑을 받으려면 먼저 일정을 추가해주세요.<br>'
            '<span style="font-size:12px;">캘린더 탭에서 직접 입력하거나, Google Calendar를 연동하세요.</span></div>'
        )
    else:
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
                    format_func=lambda v: {
                        1: "😊 매우 좋음", 2: "🙂 좋음", 3: "😐 보통",
                        4: "😔 피곤", 5: "😩 매우 피곤"
                    }[v],
                )
            condition_memo = st.text_input(
                "컨디션 메모 (선택)",
                placeholder="예: 어젯밤 술자리 / 목감기 기운이 있어요",
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
                '🔑 사이드바에서 <b>Anthropic API 키</b>를 입력하면 Claude가 자연어로 브리핑을 생성합니다.</div>'
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
    st.html('<div style="font-size:16px;font-weight:700;color:#1a1d23;margin-bottom:16px;">📊 일정 분석</div>')

    if not selected_models:
        st.html(
            '<div style="background:#f8f9fc;border:1.5px dashed #e8eaf0;border-radius:12px;'
            'padding:40px;text-align:center;color:#9ca3af;font-size:14px;">'
            '📭 분석할 일정을 먼저 추가해주세요.</div>'
        )
    else:
        briefing = generate_briefing(selected_models, analysis, persona)

        p_color = "#6366f1"
        st.html(f"""
        <div style="background:#fff;border:1px solid #e8eaf0;border-radius:12px;
                    padding:20px 24px;margin-bottom:16px;border-top:4px solid {p_color};">
          <div style="font-size:11px;color:#9ca3af;font-weight:500;text-transform:uppercase;
                      letter-spacing:.5px;margin-bottom:6px;">오늘의 유형</div>
          <div style="font-size:20px;font-weight:700;color:#1a1d23;margin-bottom:6px;">{persona['name']}</div>
          <div style="font-size:13px;color:#6b7280;line-height:1.6;">{persona['rationale']}</div>
        </div>
        """)

        if analysis["schedule_conflicts"] or analysis["insufficient_buffer_time"]:
            st.warning(briefing["risk_message"])
        else:
            st.success(briefing["risk_message"])

        st.html('<div style="font-size:14px;font-weight:600;color:#374151;margin:16px 0 8px;">추천 액션</div>')
        actions_html = "".join(
            f'<div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:8px;">'
            f'<span style="color:#6366f1;font-size:16px;flex-shrink:0;margin-top:1px;">→</span>'
            f'<span style="font-size:14px;color:#374151;line-height:1.6;">{action}</span></div>'
            for action in briefing["recommended_actions"]
        )
        st.html(f'<div style="background:#fff;border:1px solid #e8eaf0;border-radius:12px;padding:20px 24px;">{actions_html}</div>')

        if analysis["category_distribution"]:
            st.html('<div style="font-size:14px;font-weight:600;color:#374151;margin:16px 0 8px;">카테고리 분포</div>')
            total = sum(analysis["category_distribution"].values())
            bars = "".join(
                f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">'
                f'<span style="width:64px;font-size:13px;color:#6b7280;text-align:right;">{cat}</span>'
                f'<div style="flex:1;height:8px;background:#f1f5f9;border-radius:99px;overflow:hidden;">'
                f'<div style="width:{cnt/total*100:.0f}%;height:100%;'
                f'background:{CATEGORY_COLORS.get(cat,"#94a3b8")};border-radius:99px;"></div></div>'
                f'<span style="font-size:12px;color:#9ca3af;width:28px;">{cnt}개</span></div>'
                for cat, cnt in sorted(analysis["category_distribution"].items(), key=lambda x: -x[1])
            )
            st.html(f'<div style="background:#fff;border:1px solid #e8eaf0;border-radius:12px;padding:20px 24px;">{bars}</div>')

        with st.expander("🔍 분석 원본 데이터"):
            st.json(analysis)
