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
        f"You have {analysis['total_schedules']} scheduled item(s) totaling "
        f"{analysis['total_scheduled_hours']} hour(s). Today looks like a "
        f"{persona['name']} day: {persona['rationale']}"
    )


def _build_risk_message(conflict_count: int, buffer_risk_count: int) -> str:
    messages: list[str] = []

    if conflict_count:
        messages.append(f"{conflict_count} schedule conflict(s) need attention.")
    if buffer_risk_count:
        messages.append(f"{buffer_risk_count} transition(s) have insufficient buffer time.")

    if not messages:
        return "No major scheduling risks detected."

    return " ".join(messages)


def _build_recommended_actions(analysis: dict[str, Any], persona: dict[str, str]) -> list[str]:
    actions: list[str] = []

    if analysis["schedule_conflicts"]:
        actions.append("Resolve overlapping events before the day starts.")

    if analysis["insufficient_buffer_time"]:
        actions.append(
            f"Add at least {analysis['minimum_buffer_minutes']} minutes between tight transitions."
        )

    if persona["name"] == "Work-Focused Planner":
        actions.append("Block one uninterrupted focus window for the highest-leverage task.")
    elif persona["name"] == "Growth-Oriented Planner":
        actions.append("Protect learning or health blocks from being displaced by reactive work.")
    elif persona["name"] == "Life-Balanced Planner":
        actions.append("Keep boundaries clear between work commitments and personal priorities.")
    else:
        actions.append("Use open calendar space intentionally instead of filling it by default.")

    if analysis["total_scheduled_hours"] >= 8:
        actions.append("Consider moving or shortening lower-priority meetings to reduce overload.")

    return actions
