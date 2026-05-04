from __future__ import annotations

from typing import Any


def generate_life_coach_plan(
    analysis: dict[str, Any],
    persona: dict[str, str],
    day_context: dict[str, Any],
) -> dict[str, Any]:
    weather = day_context["weather"]["weather"]
    outdoor = day_context["outdoor"]
    energy = day_context["energy"]

    return {
        "headline": _build_headline(analysis, persona, day_context),
        "weather_care": _build_weather_care(weather, day_context),
        "skin_care": _build_skin_care(weather, day_context),
        "mental_care": _build_mental_care(energy, day_context),
        "meal_care": _build_meal_care(day_context),
        "prep_checklist": _build_prep_checklist(day_context),
        "signals": {
            "outdoor_schedule_count": outdoor["count"],
            "energy_level": energy["level"],
            "weather_summary": weather["summary"],
        },
    }


def _build_headline(
    analysis: dict[str, Any],
    persona: dict[str, str],
    day_context: dict[str, Any],
) -> str:
    outdoor_count = day_context["outdoor"]["count"]
    energy_level = day_context["energy"]["level"]

    return (
        f"오늘은 {analysis['total_schedules']}개의 일정과 {analysis['total_scheduled_hours']}시간의 계획이 있습니다. "
        f"{persona['name']} 성향이 강하고, 외부 이동 가능 일정은 {outdoor_count}개이며 "
        f"에너지 소모는 {energy_level} 수준으로 예상됩니다."
    )


def _build_weather_care(weather: dict[str, Any], day_context: dict[str, Any]) -> list[str]:
    actions: list[str] = []
    outdoor = day_context["outdoor"]

    if outdoor["count"]:
        actions.append(
            f"{day_context['weather']['location']} 날씨는 {weather['condition']}, "
            f"체감 {weather['feels_like_c']}도입니다. 외부 이동 전 옷차림을 한 번 점검하세요."
        )
    else:
        actions.append("오늘은 실내 중심 일정이라 날씨 영향은 크지 않습니다.")

    if day_context["care_flags"]["rain_gear"]:
        actions.append("강수 가능성이 있어 우산이나 방수 가능한 가방을 챙기세요.")

    if weather["temperature_c"] >= 24:
        actions.append("기온이 높은 편이라 물을 가까이에 두고 이동 전후로 수분을 보충하세요.")

    return actions


def _build_skin_care(weather: dict[str, Any], day_context: dict[str, Any]) -> list[str]:
    actions: list[str] = []
    flags = day_context["care_flags"]

    if flags["sun_protection"]:
        actions.append(f"자외선 지수 {weather['uv_index']}로 높은 편입니다. 외출 전 선크림을 바르세요.")

    if flags["skin_moisture"]:
        actions.append(f"습도 {weather['humidity_percent']}%로 건조한 편입니다. 세안 후 보습을 조금 더 신경 쓰세요.")

    if flags["hydration"]:
        actions.append("운동이나 더운 날씨가 포함되어 있어 피부와 컨디션을 위해 물 섭취를 늘리세요.")

    if flags["air_quality_care"]:
        actions.append(f"공기질이 {weather['air_quality']}입니다. 장시간 외부에 머무른 뒤에는 세안 루틴을 챙기세요.")

    if not actions:
        actions.append("피부 컨디션을 흔들 만한 날씨 신호는 크지 않습니다. 기본 보습 루틴만 유지하세요.")

    return actions


def _build_mental_care(energy: dict[str, Any], day_context: dict[str, Any]) -> list[str]:
    actions: list[str] = []

    if energy["drivers"]:
        actions.append("오늘 에너지 소모 요인: " + ", ".join(energy["drivers"]) + ".")

    if day_context["care_flags"]["recovery_break"]:
        actions.append("오전 대화형 일정이 몰려 있습니다. 점심 이후 15분 정도 말하지 않는 회복 시간을 확보하세요.")

    if energy["level"] == "높음":
        actions.append("하루 전체를 꽉 채우기보다 가장 중요한 일정 1개만 잘 끝내는 기준을 먼저 정하세요.")
    elif energy["level"] == "보통":
        actions.append("일정 사이 짧은 전환 시간에는 메시지 확인보다 호흡 정리와 다음 일정 준비를 우선하세요.")
    else:
        actions.append("에너지 여유가 있는 날입니다. 미뤄둔 정리나 가벼운 회고를 넣기 좋습니다.")

    return actions


def _build_meal_care(day_context: dict[str, Any]) -> list[str]:
    meal = day_context["meal"]
    body = day_context["body"]
    actions: list[str] = []

    if meal["has_lunch_plan"]:
        actions.append("점심 일정이 잡혀 있습니다. 오전 회의가 끝난 뒤 바로 이동할 수 있게 준비 시간을 남겨두세요.")
    elif meal["lunch_window_is_busy"]:
        actions.append("점심 시간대가 일정으로 걸쳐 있습니다. 11시 전후로 가벼운 식사나 간식을 준비하세요.")
    else:
        actions.append("점심 시간이 비어 있습니다. 오후 집중력을 위해 식사 시간을 먼저 확보하세요.")

    if body["has_physical_activity"]:
        actions.append("운동 일정이 있어 운동 1-2시간 전에는 부담이 적은 식사와 수분 보충을 추천합니다.")

    if not meal["has_dinner_plan"] and meal["dinner_window_is_busy"]:
        actions.append("저녁 시간대에 일정이 있습니다. 늦은 폭식을 피하려면 이동 전에 간단히 먹을 것을 정해두세요.")

    return actions


def _build_prep_checklist(day_context: dict[str, Any]) -> list[dict[str, str]]:
    flags = day_context["care_flags"]
    checklist: list[dict[str, str]] = [
        {"item": "물", "reason": "수분 보충은 일정 밀도와 컨디션 관리의 기본값입니다."}
    ]

    if flags["sun_protection"]:
        checklist.append({"item": "선크림", "reason": "자외선이 높은 외부 이동 가능 일정이 있습니다."})
    if flags["rain_gear"]:
        checklist.append({"item": "우산", "reason": "강수 가능성이 있어 외부 이동 리스크가 있습니다."})
    if flags["meal_timing"]:
        checklist.append({"item": "간단한 간식", "reason": "식사 타이밍이 밀릴 가능성이 있습니다."})
    if day_context["body"]["has_physical_activity"]:
        checklist.append({"item": "운동복 또는 여분 옷", "reason": "운동 후 컨디션과 피부 관리에 도움이 됩니다."})
    if flags["recovery_break"]:
        checklist.append({"item": "15분 회복 블록", "reason": "오전 대화형 일정 뒤 멘탈 에너지 회복이 필요합니다."})

    return checklist
