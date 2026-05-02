from __future__ import annotations

from typing import Any


WORK_CATEGORIES = {"work", "meeting", "client", "operations"}
GROWTH_CATEGORIES = {"learning", "study", "exercise", "networking"}
LIFE_CATEGORIES = {"personal", "family", "health", "social", "errand"}


def classify_persona(analysis: dict[str, Any]) -> dict[str, str]:
    total_schedules = analysis["total_schedules"]
    total_hours = analysis["total_scheduled_hours"]
    distribution = analysis["category_distribution"]

    if total_schedules <= 2 or total_hours < 3:
        return _persona(
            "Light Scheduler",
            "A low-density day with enough open space for reactive work or recovery.",
        )

    work_count = _count_categories(distribution, WORK_CATEGORIES)
    growth_count = _count_categories(distribution, GROWTH_CATEGORIES)
    life_count = _count_categories(distribution, LIFE_CATEGORIES)
    total_categorized = max(total_schedules, 1)

    work_ratio = work_count / total_categorized
    growth_ratio = growth_count / total_categorized
    life_ratio = life_count / total_categorized

    if work_ratio >= 0.5 or total_hours >= 7:
        return _persona(
            "Work-Focused Planner",
            "A work-heavy schedule where meeting load and focus protection matter most.",
        )

    if growth_ratio >= 0.35:
        return _persona(
            "Growth-Oriented Planner",
            "A day shaped around learning, health, or skill-building commitments.",
        )

    if life_ratio >= 0.35 and work_ratio < 0.5:
        return _persona(
            "Life-Balanced Planner",
            "A schedule that mixes professional commitments with personal priorities.",
        )

    return _persona(
        "Life-Balanced Planner",
        "A mixed schedule without a single dominant category.",
    )


def _count_categories(distribution: dict[str, int], categories: set[str]) -> int:
    return sum(count for category, count in distribution.items() if category in categories)


def _persona(name: str, rationale: str) -> dict[str, str]:
    return {"name": name, "rationale": rationale}
