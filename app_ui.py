from __future__ import annotations

import json
import sys
from datetime import date, datetime, time
from pathlib import Path
from uuid import uuid4

import streamlit as st


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


CATEGORY_OPTIONS = ["업무", "회의", "고객", "운영", "학습", "네트워킹", "건강", "개인", "가족"]


def load_raw_data() -> dict[str, object]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def save_raw_data(raw_data: dict[str, object]) -> None:
    DATA_PATH.write_text(json.dumps(raw_data, indent=2, ensure_ascii=False), encoding="utf-8")


def get_schedule_models(schedule_items: list[dict[str, object]]) -> list[object]:
    raw_data = {
        "date": st.session_state.schedule_date.isoformat(),
        "timezone": st.session_state.raw_data.get("timezone", "Asia/Seoul"),
        "schedules": schedule_items,
    }
    return sorted(parse_schedule_file(raw_data), key=lambda item: item.start)


def get_schedule_rows(schedule_items: list[dict[str, object]]) -> list[dict[str, object]]:
    return [schedule_to_dict(schedule) for schedule in get_schedule_models(schedule_items)]


def schedules_for_date(schedule_items: list[dict[str, object]], selected_date: date) -> list[dict[str, object]]:
    return [
        item
        for item in schedule_items
        if datetime.strptime(str(item["start"]), DATETIME_FORMAT).date() == selected_date
    ]


def initialize_state() -> None:
    if "raw_data" not in st.session_state:
        raw_data = load_raw_data()
        st.session_state.raw_data = raw_data
        st.session_state.schedule_items = list(raw_data.get("schedules", []))
        st.session_state.schedule_date = datetime.strptime(str(raw_data.get("date")), "%Y-%m-%d").date()


def add_schedule(
    title: str,
    category: str,
    selected_date: date,
    start_time: time,
    end_time: time,
    location: str,
    notes: str,
) -> tuple[bool, str]:
    start_dt = datetime.combine(selected_date, start_time)
    end_dt = datetime.combine(selected_date, end_time)

    if not title.strip():
        return False, "일정명을 입력해주세요."

    if end_dt <= start_dt:
        return False, "종료 시간은 시작 시간보다 뒤여야 합니다."

    st.session_state.schedule_items.append(
        {
            "id": f"evt-{uuid4().hex[:8]}",
            "title": title.strip(),
            "category": category,
            "start": start_dt.strftime(DATETIME_FORMAT),
            "end": end_dt.strftime(DATETIME_FORMAT),
            "location": location.strip() or "미정",
            "notes": notes.strip() or "메모 없음",
        }
    )
    return True, "일정이 추가되었습니다."


def remove_schedule(schedule_id: str) -> None:
    st.session_state.schedule_items = [
        item for item in st.session_state.schedule_items if item.get("id") != schedule_id
    ]


def persist_current_data() -> None:
    st.session_state.raw_data["date"] = st.session_state.schedule_date.isoformat()
    st.session_state.raw_data["schedules"] = st.session_state.schedule_items
    save_raw_data(st.session_state.raw_data)


def render_schedule_card(schedule: dict[str, object]) -> None:
    with st.container(border=True):
        top_columns = st.columns([3, 1])
        with top_columns[0]:
            st.markdown(f"**{schedule['title']}**")
            st.caption(f"{schedule['start']} - {schedule['end']}")
        with top_columns[1]:
            if st.button("삭제", key=f"delete-{schedule['id']}"):
                remove_schedule(str(schedule["id"]))
                st.rerun()

        st.write(f"{schedule['category']} · {schedule['location']}")
        st.caption(str(schedule["notes"]))


st.set_page_config(page_title="캘린더 브리핑 에이전트", layout="wide")
initialize_state()

st.title("캘린더 브리핑 에이전트")
st.caption("일정을 직접 입력하고, 하루의 리스크와 추천 액션을 바로 확인하는 캘린더 브리핑 MVP입니다.")

selected_date = st.date_input("브리핑 날짜", value=st.session_state.schedule_date)
st.session_state.schedule_date = selected_date

selected_items = schedules_for_date(st.session_state.schedule_items, selected_date)
selected_models = get_schedule_models(selected_items)
selected_rows = get_schedule_rows(selected_items)

analysis = analyze_schedule(selected_models) if selected_models else None
persona = classify_persona(analysis) if analysis else None

summary_columns = st.columns(4)
summary_columns[0].metric("선택한 날짜", selected_date.strftime("%Y-%m-%d"))
summary_columns[1].metric("전체 일정 수", analysis["total_schedules"] if analysis else 0)
summary_columns[2].metric("총 일정 시간", analysis["total_scheduled_hours"] if analysis else 0)
summary_columns[3].metric("오늘의 유형", persona["name"] if persona else "일정 없음")

calendar_tab, briefing_tab = st.tabs(["캘린더", "데일리 브리핑"])

with calendar_tab:
    input_column, list_column = st.columns([1, 1.4])

    with input_column:
        st.subheader("일정 추가")
        with st.form("schedule-form", clear_on_submit=True):
            title = st.text_input("일정명", placeholder="예: 고객 인터뷰")
            category = st.selectbox("카테고리", CATEGORY_OPTIONS)
            start_time = st.time_input("시작 시간", value=time(9, 0), step=900)
            end_time = st.time_input("종료 시간", value=time(10, 0), step=900)
            location = st.text_input("장소", placeholder="예: 구글 미트")
            notes = st.text_area("메모", placeholder="이 일정에서 준비하거나 확인할 내용을 적어주세요.")
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
            st.success("data/sample_schedule.json에 저장했습니다.")

    with list_column:
        st.subheader("일정 목록")
        if not selected_rows:
            st.info("선택한 날짜에 등록된 일정이 없습니다. 왼쪽에서 새 일정을 추가해보세요.")
        else:
            for schedule in selected_rows:
                render_schedule_card(schedule)

        with st.expander("표로 보기"):
            st.dataframe(
                selected_rows,
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

with briefing_tab:
    st.subheader("데일리 브리핑")

    if not selected_models:
        st.info("브리핑을 생성하려면 선택한 날짜에 일정을 추가해주세요.")
    elif st.button("일정 분석하기", type="primary"):
        briefing = generate_briefing(selected_models, analysis, persona)

        persona_column, summary_column = st.columns(2)
        persona_column.metric("사용자 페르소나", persona["name"])
        persona_column.write(persona["rationale"])
        summary_column.metric("전체 일정 수", analysis["total_schedules"])
        summary_column.metric("총 일정 시간", analysis["total_scheduled_hours"])

        st.warning(briefing["risk_message"])

        st.markdown("#### 추천 액션")
        for action in briefing["recommended_actions"]:
            st.write(f"- {action}")

        with st.expander("분석 상세 보기"):
            st.json(analysis)
