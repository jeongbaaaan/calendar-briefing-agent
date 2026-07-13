"""
Claude API integration — generates a personal secretary-style wellness briefing.
Falls back to a rule-based message if ANTHROPIC_API_KEY is not set.
"""
from __future__ import annotations

import os
from typing import Any, Generator

from schema import Schedule


SYSTEM_PROMPT = """당신은 사용자의 하루 일정을 누구보다 잘 파악하고 있는 따뜻하고 세심한 AI 개인 비서입니다.

역할:
- 오늘 일정을 바탕으로 건강·컨디션·바이오리듬·이동 경로 관점에서 맞춤 조언을 드립니다.
- 딱딱한 분석 보고서가 아닌, 아침에 옆에서 말해주는 비서처럼 자연스럽고 따뜻한 말투로 이야기합니다.
- 사용자가 미처 챙기지 못한 부분을 먼저 짚어주는 선제적 비서입니다.
- 구체적인 시간대와 실행 가능한 행동을 제안합니다.

말투 원칙:
- "오늘 일정을 보니..." 로 자연스럽게 시작
- 존댓말, 따뜻하고 프로답게
- 400~600자 사이, 핵심만 짚기
- 섹션 헤더 없이 대화체로 흘러가도록
- 이모지 1~2개 정도 자연스럽게 활용"""


def _build_prompt(
    schedules: list[Schedule],
    analysis: dict[str, Any],
    wellness: dict[str, Any],
    persona: dict[str, str],
    user_condition: dict[str, Any] | None,
) -> str:
    ordered = sorted(schedules, key=lambda s: s.start)

    lines = []
    for s in ordered:
        loc = f" @ {s.location}" if s.location else ""
        lines.append(f"- {s.start.strftime('%H:%M')}~{s.end.strftime('%H:%M')} [{s.category}] {s.title}{loc}")
    schedule_text = "\n".join(lines)

    risks = []
    for r in wellness.get("fatigue_risks", []):
        risks.append(r["description"])
    for r in wellness.get("meal_risks", []):
        risks.append(r["description"])
    for r in wellness.get("travel_risks", []):
        risks.append(r["description"])
    for m in wellness.get("biorhythm_mismatches", []):
        risks.append(m)
    if not wellness.get("has_movement"):
        risks.append("오늘 일정에 신체 활동이 없습니다.")
    if wellness.get("screen_heavy"):
        risks.append("화면 기반 일정이 많아 눈·목 피로가 예상됩니다.")
    risk_text = "\n".join(f"- {r}" for r in risks) if risks else "- 특별한 건강 리스크 없음"

    condition_lines = []
    if user_condition:
        if user_condition.get("sleep_hours"):
            condition_lines.append(f"어젯밤 수면: {user_condition['sleep_hours']}시간")
        if user_condition.get("fatigue_level"):
            condition_lines.append(f"현재 피로도: {user_condition['fatigue_level']}/5")
        if user_condition.get("memo"):
            condition_lines.append(f"오늘 컨디션 메모: {user_condition['memo']}")
    condition_text = "\n".join(f"- {c}" for c in condition_lines) if condition_lines else "- 미입력"

    conflicts = analysis.get("schedule_conflicts", [])
    conflict_text = ""
    if conflicts:
        conflict_text = "\n충돌 일정:\n" + "\n".join(
            f"- {c['first']} ↔ {c['second']} ({c['overlap_minutes']}분 겹침)"
            for c in conflicts
        )

    return f"""오늘 일정 ({len(ordered)}개, 총 {analysis['total_scheduled_hours']}시간):
{schedule_text}

건강/컨디션 리스크:
{risk_text}

사용자 오늘 컨디션:
{condition_text}

페르소나: {persona['name']} — {persona['rationale']}{conflict_text}

위 내용을 바탕으로 개인 비서로서 오늘 하루를 잘 보낼 수 있도록 브리핑해주세요.
건강·컨디션·바이오리듬·이동 경로 관점에서 사용자가 놓칠 수 있는 부분을 먼저 챙겨주세요."""


def generate(
    schedules: list[Schedule],
    analysis: dict[str, Any],
    wellness: dict[str, Any],
    persona: dict[str, str],
    user_condition: dict[str, Any] | None = None,
    stream: bool = False,
) -> str | Generator[str, None, None]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return _fallback(wellness, persona)

    try:
        import anthropic
    except ImportError:
        return _fallback(wellness, persona)

    client = anthropic.Anthropic(api_key=api_key)
    prompt = _build_prompt(schedules, analysis, wellness, persona, user_condition)

    if stream:
        return _stream(client, prompt)

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=900,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def _stream(client: Any, prompt: str) -> Generator[str, None, None]:
    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=900,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        yield from stream.text_stream


def _fallback(wellness: dict[str, Any], persona: dict[str, str]) -> str:
    parts = [f"오늘은 '{persona['name']}'으로 분류된 하루입니다. {persona['rationale']}"]

    for r in wellness.get("fatigue_risks", []):
        parts.append(r["description"])
    for r in wellness.get("meal_risks", []):
        parts.append(r["description"])
    for r in wellness.get("travel_risks", []):
        parts.append(r["description"])

    if not wellness.get("has_movement"):
        parts.append("오늘 운동 일정이 없습니다. 점심 후 10분 산책을 추천합니다.")
    if wellness.get("screen_heavy"):
        parts.append("화면 작업이 많은 날입니다. 20분마다 20초씩 먼 곳을 바라보세요.")

    return " ".join(parts)
