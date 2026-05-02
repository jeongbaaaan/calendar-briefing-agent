from __future__ import annotations

from typing import Any

from schema import Schedule, schedule_to_dict


def generate_briefing(
    schedules: list[Schedule],
    analysis: dict[str, Any],
    persona: dict[str, str],
) -> dict[str, Any]:
    ordered = sorted(schedules, key=lambda item: item.start)
    conflict_count = len(analysis["schedule_conflicts"])
    buffer_risk_count = len(analysis["insufficient_buffer_time"])

    return {
        "summary": _build_summary(analysis, persona),
        "persona": persona,
        "schedule_list": [schedule_to_dict(item) for item in ordered],
        "risk_message": _build_risk_message(conflict_count, buffer_risk_count),
        "recommended_actions": _build_recommended_actions(analysis, persona),
    }


def _build_summary(analysis: dict[str, Any], persona: dict[str, str]) -> str:
    return (
        f"오늘은 총 {analysis['total_schedules']}개의 일정이 있으며, "
        f"전체 일정 시간은 {analysis['total_scheduled_hours']}시간입니다. "
        f"오늘의 유형은 '{persona['name']}'입니다. {persona['rationale']}"
    )


def _build_risk_message(conflict_count: int, buffer_risk_count: int) -> str:
    messages: list[str] = []

    if conflict_count:
        messages.append(f"겹치는 일정 {conflict_count}건을 확인해야 합니다.")
    if buffer_risk_count:
        messages.append(f"이동 또는 전환 시간이 부족한 구간이 {buffer_risk_count}건 있습니다.")

    if not messages:
        return "큰 일정 리스크는 발견되지 않았습니다."

    return " ".join(messages)


def _build_recommended_actions(analysis: dict[str, Any], persona: dict[str, str]) -> list[str]:
    actions: list[str] = []

    if analysis["schedule_conflicts"]:
        actions.append("하루를 시작하기 전에 겹치는 일정을 먼저 조정하세요.")

    if analysis["insufficient_buffer_time"]:
        actions.append(
            f"일정 사이에 최소 {analysis['minimum_buffer_minutes']}분 이상의 전환 시간을 확보하세요."
        )

    if persona["name"] == "업무 집중형 플래너":
        actions.append("가장 중요한 업무를 위해 방해받지 않는 집중 시간을 하나 확보하세요.")
    elif persona["name"] == "성장 지향형 플래너":
        actions.append("학습이나 건강 관련 일정이 급한 업무에 밀리지 않도록 보호하세요.")
    elif persona["name"] == "균형 생활형 플래너":
        actions.append("업무 일정과 개인 일정 사이의 경계를 명확히 유지하세요.")
    else:
        actions.append("비어 있는 시간을 무작정 채우기보다 의도적으로 활용하세요.")

    if analysis["total_scheduled_hours"] >= 8:
        actions.append("일정 과부하를 줄이기 위해 우선순위가 낮은 회의는 이동하거나 줄이는 것을 검토하세요.")

    return actions
