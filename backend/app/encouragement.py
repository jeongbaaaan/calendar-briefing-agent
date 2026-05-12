from __future__ import annotations

from typing import Any


def generate_encouragement(
    analysis: dict[str, Any],
    persona: dict[str, str],
) -> dict[str, Any]:
    conflict_count = len(analysis["schedule_conflicts"])
    buffer_count = len(analysis["insufficient_buffer_time"])
    total_hours = analysis["total_scheduled_hours"]

    if conflict_count or buffer_count >= 2:
        message = (
            "오늘은 빈틈이 많지 않은 하루예요. 모든 걸 완벽하게 해내려고 하기보다, "
            "가장 중요한 일정 하나를 무사히 넘기는 것만으로도 충분합니다."
        )
    elif total_hours >= 7:
        message = (
            "일정이 길게 이어지는 날이에요. 지치지 않는 사람이 되는 것보다, "
            "중간중간 나를 회복시키는 사람이 되는 쪽이 더 오래 갑니다."
        )
    elif persona["name"] == "가벼운 일정형":
        message = (
            "오늘은 조금 비어 있는 하루예요. 방향을 바로 정하지 못해도 괜찮습니다. "
            "작은 정리 하나, 짧은 산책 하나처럼 부담 없는 시작이면 충분해요."
        )
    else:
        message = (
            "오늘 원하는 게 또렷하지 않아도 괜찮아요. 하루 전체를 결정하려 하지 말고, "
            "지금 할 수 있는 작은 선택 하나만 골라도 충분합니다."
        )

    return {
        "title": "오늘의 작은 응원",
        "message": message,
        "reminders": [
            "모든 답을 오늘 정하지 않아도 괜찮아요.",
            "해야 할 일을 줄이는 것도 좋은 선택입니다.",
            "오늘의 기준은 완벽함보다 회복에 가까워도 됩니다.",
        ],
    }
