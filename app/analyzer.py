from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from typing import Any

from schema import BufferRisk, Conflict, Schedule


DEFAULT_MINIMUM_BUFFER_MINUTES = 15


def analyze_schedule(
    schedules: list[Schedule],
    minimum_buffer_minutes: int = DEFAULT_MINIMUM_BUFFER_MINUTES,
) -> dict[str, Any]:
    ordered = sorted(schedules, key=lambda item: item.start)
    category_distribution = Counter(item.category for item in ordered)

    conflicts = _find_conflicts(ordered)
    buffer_risks = _find_buffer_risks(ordered, minimum_buffer_minutes)

    return {
        "total_schedules": len(ordered),
        "total_scheduled_hours": round(sum(item.duration_hours for item in ordered), 2),
        "category_distribution": dict(sorted(category_distribution.items())),
        "schedule_conflicts": [asdict(conflict) for conflict in conflicts],
        "insufficient_buffer_time": [asdict(risk) for risk in buffer_risks],
        "minimum_buffer_minutes": minimum_buffer_minutes,
    }


def _find_conflicts(ordered_schedules: list[Schedule]) -> list[Conflict]:
    conflicts: list[Conflict] = []

    for index, current in enumerate(ordered_schedules):
        for candidate in ordered_schedules[index + 1 :]:
            if candidate.start >= current.end:
                break

            overlap_minutes = int((min(current.end, candidate.end) - candidate.start).total_seconds() / 60)
            conflicts.append(
                Conflict(
                    first=current.title,
                    second=candidate.title,
                    overlap_minutes=overlap_minutes,
                )
            )

    return conflicts


def _find_buffer_risks(
    ordered_schedules: list[Schedule],
    minimum_buffer_minutes: int,
) -> list[BufferRisk]:
    risks: list[BufferRisk] = []

    for previous, next_item in zip(ordered_schedules, ordered_schedules[1:]):
        if next_item.start < previous.end:
            continue

        buffer_minutes = int((next_item.start - previous.end).total_seconds() / 60)
        if buffer_minutes < minimum_buffer_minutes:
            risks.append(
                BufferRisk(
                    previous=previous.title,
                    next=next_item.title,
                    buffer_minutes=buffer_minutes,
                    recommended_minimum_minutes=minimum_buffer_minutes,
                )
            )

    return risks
