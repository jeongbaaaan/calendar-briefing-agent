from __future__ import annotations

from typing import Any

from schema import Schedule


INDOOR_KEYWORDS = {
    "zoom",
    "meet",
    "구글 미트",
    "줌",
    "회의실",
    "책상",
    "온라인",
    "화상",
    "사무실",
}
OUTDOOR_KEYWORDS = {
    "강남",
    "공원",
    "야외",
    "외부",
    "이동",
    "산책",
    "방문",
    "카페",
    "역",
}
MEAL_KEYWORDS = {"아침", "점심", "저녁", "식사", "브런치", "런치", "디너"}
SOCIAL_CATEGORIES = {"meeting", "client", "networking", "회의", "고객", "네트워킹"}
PHYSICAL_CATEGORIES = {"exercise", "health", "운동", "건강"}


def parse_weather_file(raw_data: dict[str, Any]) -> dict[str, Any]:
    weather = raw_data.get("weather")
    if not isinstance(weather, dict):
        raise ValueError("Weather JSON must contain a 'weather' object.")

    required_fields = {
        "condition",
        "temperature_c",
        "feels_like_c",
        "precipitation_probability",
        "uv_index",
        "humidity_percent",
        "air_quality",
        "summary",
    }
    missing_fields = required_fields - weather.keys()
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ValueError(f"Weather data is missing required field(s): {missing}")

    return {
        "date": raw_data.get("date"),
        "location": raw_data.get("location", "알 수 없음"),
        "weather": weather,
    }


def build_day_context(schedules: list[Schedule], weather_data: dict[str, Any]) -> dict[str, Any]:
    ordered = sorted(schedules, key=lambda item: item.start)
    weather = weather_data["weather"]
    outdoor_schedules = [schedule for schedule in ordered if _is_outdoor_schedule(schedule)]
    meal_schedules = [schedule for schedule in ordered if _is_meal_schedule(schedule)]
    physical_schedules = [schedule for schedule in ordered if _is_physical_schedule(schedule)]

    return {
        "weather": weather_data,
        "outdoor": {
            "count": len(outdoor_schedules),
            "titles": [schedule.title for schedule in outdoor_schedules],
            "has_many": len(outdoor_schedules) >= 2,
        },
        "meal": _build_meal_context(ordered, meal_schedules),
        "energy": _build_energy_context(ordered, outdoor_schedules),
        "body": {
            "has_physical_activity": bool(physical_schedules),
            "physical_titles": [schedule.title for schedule in physical_schedules],
        },
        "care_flags": {
            "sun_protection": weather["uv_index"] >= 6 and bool(outdoor_schedules),
            "rain_gear": weather["precipitation_probability"] >= 40 and bool(outdoor_schedules),
            "hydration": weather["temperature_c"] >= 24 or bool(physical_schedules),
            "skin_moisture": weather["humidity_percent"] <= 45,
            "air_quality_care": weather["air_quality"] in {"나쁨", "매우 나쁨"},
            "recovery_break": _needs_recovery_break(ordered),
            "meal_timing": len(meal_schedules) == 0 or _has_long_gap_without_meal(ordered, meal_schedules),
        },
    }


def _is_outdoor_schedule(schedule: Schedule) -> bool:
    text = _schedule_text(schedule)
    if any(keyword in text for keyword in INDOOR_KEYWORDS):
        return False
    return any(keyword in text for keyword in OUTDOOR_KEYWORDS)


def _is_meal_schedule(schedule: Schedule) -> bool:
    return any(keyword in _schedule_text(schedule) for keyword in MEAL_KEYWORDS)


def _is_physical_schedule(schedule: Schedule) -> bool:
    return schedule.category in PHYSICAL_CATEGORIES or "운동" in _schedule_text(schedule)


def _build_meal_context(
    ordered_schedules: list[Schedule],
    meal_schedules: list[Schedule],
) -> dict[str, Any]:
    lunch_window_is_busy = any(
        schedule.start.hour < 13 and schedule.end.hour >= 11 for schedule in ordered_schedules
    )
    dinner_window_is_busy = any(
        schedule.start.hour < 20 and schedule.end.hour >= 18 for schedule in ordered_schedules
    )

    return {
        "meal_titles": [schedule.title for schedule in meal_schedules],
        "has_lunch_plan": any("점심" in _schedule_text(schedule) for schedule in meal_schedules),
        "has_dinner_plan": any("저녁" in _schedule_text(schedule) for schedule in meal_schedules),
        "lunch_window_is_busy": lunch_window_is_busy,
        "dinner_window_is_busy": dinner_window_is_busy,
    }


def _build_energy_context(
    ordered_schedules: list[Schedule],
    outdoor_schedules: list[Schedule],
) -> dict[str, Any]:
    social_count = sum(1 for schedule in ordered_schedules if schedule.category in SOCIAL_CATEGORIES)
    dense_blocks = sum(
        1
        for previous, next_item in zip(ordered_schedules, ordered_schedules[1:])
        if 0 <= (next_item.start - previous.end).total_seconds() / 60 < 20
    )
    score = social_count + dense_blocks + len(outdoor_schedules)

    if score >= 6:
        level = "높음"
    elif score >= 3:
        level = "보통"
    else:
        level = "낮음"

    drivers: list[str] = []
    if social_count:
        drivers.append(f"대화/회의성 일정 {social_count}개")
    if dense_blocks:
        drivers.append(f"20분 미만 전환 구간 {dense_blocks}개")
    if outdoor_schedules:
        drivers.append(f"외부 이동 가능 일정 {len(outdoor_schedules)}개")

    return {"level": level, "score": score, "drivers": drivers}


def _needs_recovery_break(ordered_schedules: list[Schedule]) -> bool:
    morning_social_count = sum(
        1
        for schedule in ordered_schedules
        if schedule.start.hour < 12 and schedule.category in SOCIAL_CATEGORIES
    )
    return morning_social_count >= 2


def _has_long_gap_without_meal(
    ordered_schedules: list[Schedule],
    meal_schedules: list[Schedule],
) -> bool:
    if meal_schedules or not ordered_schedules:
        return False

    first_start = ordered_schedules[0].start
    last_end = max(schedule.end for schedule in ordered_schedules)
    return (last_end - first_start).total_seconds() / 3600 >= 6


def _schedule_text(schedule: Schedule) -> str:
    return " ".join(
        part.lower()
        for part in [
            schedule.title,
            schedule.category,
            schedule.location or "",
            schedule.notes or "",
        ]
    )
