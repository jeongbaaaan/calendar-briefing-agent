from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


DATETIME_FORMAT = "%Y-%m-%d %H:%M"


@dataclass(frozen=True)
class Schedule:
    id: str
    title: str
    category: str
    start: datetime
    end: datetime
    location: str | None = None
    notes: str | None = None

    @property
    def duration_hours(self) -> float:
        return round((self.end - self.start).total_seconds() / 3600, 2)


@dataclass(frozen=True)
class Conflict:
    first: str
    second: str
    overlap_minutes: int


@dataclass(frozen=True)
class BufferRisk:
    previous: str
    next: str
    buffer_minutes: int
    recommended_minimum_minutes: int


def parse_schedule(raw_item: dict[str, Any]) -> Schedule:
    required_fields = {"id", "title", "category", "start", "end"}
    missing_fields = required_fields - raw_item.keys()
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ValueError(f"Schedule item is missing required field(s): {missing}")

    start = datetime.strptime(raw_item["start"], DATETIME_FORMAT)
    end = datetime.strptime(raw_item["end"], DATETIME_FORMAT)
    if end <= start:
        raise ValueError(f"Schedule '{raw_item['title']}' must end after it starts.")

    return Schedule(
        id=str(raw_item["id"]),
        title=str(raw_item["title"]),
        category=str(raw_item["category"]).lower(),
        start=start,
        end=end,
        location=raw_item.get("location"),
        notes=raw_item.get("notes"),
    )


def parse_schedule_file(raw_data: dict[str, Any]) -> list[Schedule]:
    schedules = raw_data.get("schedules")
    if not isinstance(schedules, list):
        raise ValueError("Input JSON must contain a 'schedules' list.")

    return [parse_schedule(item) for item in schedules]


def schedule_to_dict(schedule: Schedule) -> dict[str, Any]:
    return {
        "id": schedule.id,
        "title": schedule.title,
        "category": schedule.category,
        "start": schedule.start.strftime(DATETIME_FORMAT),
        "end": schedule.end.strftime(DATETIME_FORMAT),
        "duration_hours": schedule.duration_hours,
        "location": schedule.location,
        "notes": schedule.notes,
    }
