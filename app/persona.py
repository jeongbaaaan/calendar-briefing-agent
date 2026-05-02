from __future__ import annotations

from typing import Any


WORK_CATEGORIES = {"work", "meeting", "client", "operations", "업무", "회의", "고객", "운영"}
GROWTH_CATEGORIES = {"learning", "study", "exercise", "networking", "학습", "공부", "운동", "네트워킹"}
LIFE_CATEGORIES = {"personal", "family", "health", "social", "errand", "개인", "가족", "건강", "소셜", "심부름"}


def classify_persona(analysis: dict[str, Any]) -> dict[str, str]:
    total_schedules = analysis["total_schedules"]
    total_hours = analysis["total_scheduled_hours"]
    distribution = analysis["category_distribution"]

    if total_schedules <= 2 or total_hours < 3:
        return _persona(
            "가벼운 일정형",
            "일정 밀도가 낮아 즉흥 업무나 회복을 위한 여유가 있는 하루입니다.",
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
            "업무 집중형 플래너",
            "업무 비중이 높아 회의 부담 관리와 집중 시간 확보가 중요한 하루입니다.",
        )

    if growth_ratio >= 0.35:
        return _persona(
            "성장 지향형 플래너",
            "학습, 건강, 역량 개발 일정이 중심이 되는 하루입니다.",
        )

    if life_ratio >= 0.35 and work_ratio < 0.5:
        return _persona(
            "균형 생활형 플래너",
            "업무 일정과 개인 우선순위가 함께 배치된 균형형 일정입니다.",
        )

    return _persona(
        "균형 생활형 플래너",
        "특정 카테고리에 지나치게 치우치지 않은 혼합형 일정입니다.",
    )


def _count_categories(distribution: dict[str, int], categories: set[str]) -> int:
    return sum(count for category, count in distribution.items() if category in categories)


def _persona(name: str, rationale: str) -> dict[str, str]:
    return {"name": name, "rationale": rationale}
