"""
Analyzes schedule data for health, condition, biorhythm, and travel signals.
Produces structured wellness insights that feed into the secretary AI prompt.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from schema import Schedule


SCREEN_KEYWORDS = {"줌", "zoom", "미트", "meet", "화상", "온라인", "remote", "책상", "desk"}
WORK_CATEGORIES = {"업무", "회의", "고객", "운영", "work", "meeting", "client", "operations"}
HEALTH_CATEGORIES = {"건강", "운동", "health", "exercise"}

# Biorhythm energy windows as (start_hour, end_hour, label, description)
ENERGY_WINDOWS = [
    (9.0, 11.5, "피크", "집중력·창의성이 가장 높은 시간대"),
    (11.5, 13.0, "보통", "점심 전 마무리 업무 시간"),
    (13.0, 14.5, "저하", "점심 후 졸음·집중력 저하 구간"),
    (14.5, 17.0, "피크", "오후 집중 회복 구간"),
    (17.0, 19.0, "보통", "마무리·가벼운 업무 시간"),
    (19.0, 23.0, "저하", "신체·인지 회복이 필요한 저녁"),
]

MEAL_WINDOWS = {
    "아침": (7.0, 9.0),
    "점심": (11.5, 13.5),
    "저녁": (18.0, 20.0),
}

MAX_CONTINUOUS_WORK_HOURS = 2.0
MIN_SCREEN_BREAK_MINUTES = 90
TRAVEL_BUFFER_MINUTES = 25


@dataclass
class MealRisk:
    meal: str
    description: str


@dataclass
class FatigueRisk:
    kind: str
    start_time: str
    end_time: str
    description: str


@dataclass
class TravelRisk:
    from_event: str
    to_event: str
    from_location: str
    to_location: str
    buffer_minutes: int
    description: str


def _to_hour(dt: datetime) -> float:
    return dt.hour + dt.minute / 60


def _is_screen(location: str | None) -> bool:
    if not location:
        return False
    loc = location.lower()
    return any(kw in loc for kw in SCREEN_KEYWORDS)


def _is_virtual(location: str | None) -> bool:
    if not location:
        return False
    loc = location.lower()
    return any(kw in loc for kw in {"줌", "zoom", "미트", "meet", "온라인", "화상"})


def analyze_wellness(
    schedules: list[Schedule],
    sleep_hours: float | None = None,
    fatigue_level: int | None = None,
) -> dict[str, Any]:
    if not schedules:
        return _empty()

    ordered = sorted(schedules, key=lambda s: s.start)

    return {
        "energy_curve": _build_energy_curve(ordered),
        "meal_risks": [
            {"meal": r.meal, "description": r.description}
            for r in _check_meal_risks(ordered)
        ],
        "fatigue_risks": [
            {"kind": r.kind, "start": r.start_time, "end": r.end_time, "description": r.description}
            for r in _check_fatigue_risks(ordered, sleep_hours, fatigue_level)
        ],
        "travel_risks": [
            {
                "from_event": r.from_event,
                "to_event": r.to_event,
                "buffer_minutes": r.buffer_minutes,
                "description": r.description,
            }
            for r in _check_travel_risks(ordered)
        ],
        "has_movement": any(s.category in HEALTH_CATEGORIES for s in ordered),
        "screen_heavy": _is_screen_heavy(ordered),
        "first_event_hour": _to_hour(ordered[0].start),
        "last_event_hour": _to_hour(ordered[-1].end),
        "longest_continuous_block_hours": _longest_continuous_block(ordered),
        "biorhythm_mismatches": _check_biorhythm_mismatches(ordered),
        "sleep_hours": sleep_hours,
        "fatigue_level": fatigue_level,
    }


def _build_energy_curve(ordered: list[Schedule]) -> list[dict[str, Any]]:
    result = []
    for start_h, end_h, label, desc in ENERGY_WINDOWS:
        events_in_window = [
            s.title
            for s in ordered
            if _to_hour(s.start) < end_h and _to_hour(s.end) > start_h
        ]
        result.append({
            "hour_start": start_h,
            "hour_end": end_h,
            "label": label,
            "description": desc,
            "events": events_in_window,
        })
    return result


def _check_meal_risks(ordered: list[Schedule]) -> list[MealRisk]:
    risks = []
    for meal, (start_h, end_h) in MEAL_WINDOWS.items():
        blocking = [
            s for s in ordered
            if _to_hour(s.start) < end_h
            and _to_hour(s.end) > start_h
            and s.category in WORK_CATEGORIES
        ]
        if blocking and meal in ("점심", "저녁"):
            titles = "·".join(s.title for s in blocking[:2])
            risks.append(MealRisk(
                meal=meal,
                description=(
                    f"{meal} 시간대({int(start_h)}시~{int(end_h)}시)에 '{titles}' 일정이 있어 "
                    f"식사 시간이 충분하지 않을 수 있습니다."
                ),
            ))
    return risks


def _check_fatigue_risks(
    ordered: list[Schedule],
    sleep_hours: float | None,
    fatigue_level: int | None,
) -> list[FatigueRisk]:
    risks = []

    # Early start
    if _to_hour(ordered[0].start) < 8.5:
        risks.append(FatigueRisk(
            kind="조기_기상",
            start_time=ordered[0].start.strftime("%H:%M"),
            end_time="",
            description=f"첫 일정이 {ordered[0].start.strftime('%H:%M')}으로 이릅니다. 준비 루틴을 미리 챙기세요.",
        ))

    # Sleep deprivation
    if sleep_hours is not None and sleep_hours < 6.5:
        risks.append(FatigueRisk(
            kind="수면_부족",
            start_time="",
            end_time="",
            description=f"어젯밤 수면이 {sleep_hours}시간으로 권장(7~8시간) 대비 부족합니다. 오후 집중력 저하에 대비하세요.",
        ))

    # High fatigue self-report
    if fatigue_level is not None and fatigue_level >= 4:
        risks.append(FatigueRisk(
            kind="높은_피로도",
            start_time="",
            end_time="",
            description=f"현재 피로도가 {fatigue_level}/5로 높습니다. 오늘 회의 전 5분 눈 감기와 깊은 호흡을 추천합니다.",
        ))

    # Continuous work blocks
    risks.extend(_find_continuous_work_risks(ordered))

    # Screen fatigue
    risks.extend(_find_screen_fatigue_risks(ordered))

    return risks


def _find_continuous_work_risks(ordered: list[Schedule]) -> list[FatigueRisk]:
    risks = []
    block_start: datetime | None = None
    block_end: datetime | None = None

    def _flush(bs: datetime, be: datetime) -> FatigueRisk | None:
        hours = (be - bs).total_seconds() / 3600
        if hours >= MAX_CONTINUOUS_WORK_HOURS:
            return FatigueRisk(
                kind="연속_업무",
                start_time=bs.strftime("%H:%M"),
                end_time=be.strftime("%H:%M"),
                description=(
                    f"{bs.strftime('%H:%M')}~{be.strftime('%H:%M')} {hours:.1f}시간 연속 업무입니다. "
                    f"중간에 5분 스트레칭 또는 물 한 잔을 챙기세요."
                ),
            )
        return None

    for s in ordered:
        if s.category in WORK_CATEGORIES:
            if block_start is None:
                block_start = s.start
                block_end = s.end
            else:
                gap_min = (s.start - block_end).total_seconds() / 60
                if gap_min <= 15:
                    block_end = max(block_end, s.end)
                else:
                    if block_start and block_end:
                        r = _flush(block_start, block_end)
                        if r:
                            risks.append(r)
                    block_start = s.start
                    block_end = s.end
        else:
            if block_start and block_end:
                r = _flush(block_start, block_end)
                if r:
                    risks.append(r)
            block_start = None
            block_end = None

    if block_start and block_end:
        r = _flush(block_start, block_end)
        if r:
            risks.append(r)

    return risks


def _find_screen_fatigue_risks(ordered: list[Schedule]) -> list[FatigueRisk]:
    risks = []
    block_start: datetime | None = None
    block_end: datetime | None = None

    for s in ordered:
        if _is_screen(s.location):
            if block_start is None:
                block_start = s.start
                block_end = s.end
            else:
                gap_min = (s.start - block_end).total_seconds() / 60
                if gap_min <= 20:
                    block_end = max(block_end, s.end)
                else:
                    mins = (block_end - block_start).total_seconds() / 60  # type: ignore[union-attr]
                    if mins >= MIN_SCREEN_BREAK_MINUTES:
                        risks.append(FatigueRisk(
                            kind="화면_피로",
                            start_time=block_start.strftime("%H:%M"),  # type: ignore[union-attr]
                            end_time=block_end.strftime("%H:%M"),  # type: ignore[union-attr]
                            description=(
                                f"{block_start.strftime('%H:%M')}~{block_end.strftime('%H:%M')} "  # type: ignore[union-attr]
                                f"화면 연속 {int(mins)}분. 20-20-20 법칙(20분마다 20초, 6m 거리 응시)을 지키세요."
                            ),
                        ))
                    block_start = s.start
                    block_end = s.end
        else:
            block_start = None
            block_end = None

    return risks


def _check_travel_risks(ordered: list[Schedule]) -> list[TravelRisk]:
    risks = []
    for prev, curr in zip(ordered, ordered[1:]):
        prev_loc = (prev.location or "").strip()
        curr_loc = (curr.location or "").strip()

        if not prev_loc or not curr_loc:
            continue
        if prev_loc == curr_loc:
            continue
        if _is_virtual(prev_loc) or _is_virtual(curr_loc):
            continue

        buffer_min = int((curr.start - prev.end).total_seconds() / 60)
        if buffer_min < TRAVEL_BUFFER_MINUTES:
            risks.append(TravelRisk(
                from_event=prev.title,
                to_event=curr.title,
                from_location=prev_loc,
                to_location=curr_loc,
                buffer_minutes=buffer_min,
                description=(
                    f"'{prev.title}' 끝나고 {buffer_min}분 안에 '{curr_loc}'로 이동해야 합니다. "
                    f"이동 여유가 부족하니 미리 자리를 뜰 준비를 해두세요."
                ),
            ))
    return risks


def _is_screen_heavy(ordered: list[Schedule]) -> bool:
    if not ordered:
        return False
    screen_count = sum(1 for s in ordered if _is_screen(s.location))
    return screen_count >= len(ordered) * 0.5


def _longest_continuous_block(ordered: list[Schedule]) -> float:
    if not ordered:
        return 0.0
    max_h = 0.0
    bs = ordered[0].start
    be = ordered[0].end
    for s in ordered[1:]:
        gap = (s.start - be).total_seconds() / 60
        if gap <= 15:
            be = max(be, s.end)
        else:
            max_h = max(max_h, (be - bs).total_seconds() / 3600)
            bs = s.start
            be = s.end
    max_h = max(max_h, (be - bs).total_seconds() / 3600)
    return round(max_h, 2)


def _check_biorhythm_mismatches(ordered: list[Schedule]) -> list[str]:
    dip_windows = [(h_start, h_end) for h_start, h_end, label, _ in ENERGY_WINDOWS if label == "저하"]
    mismatches = []
    for s in ordered:
        if s.category not in WORK_CATEGORIES:
            continue
        h = _to_hour(s.start)
        for dip_s, dip_e in dip_windows:
            if dip_s <= h < dip_e:
                mismatches.append(
                    f"'{s.title}'이 에너지 저하 구간({int(dip_s)}시~{int(dip_e)}시)에 잡혀 있습니다."
                )
    return mismatches


def _empty() -> dict[str, Any]:
    return {
        "energy_curve": [],
        "meal_risks": [],
        "fatigue_risks": [],
        "travel_risks": [],
        "has_movement": False,
        "screen_heavy": False,
        "first_event_hour": None,
        "last_event_hour": None,
        "longest_continuous_block_hours": 0.0,
        "biorhythm_mismatches": [],
        "sleep_hours": None,
        "fatigue_level": None,
    }
