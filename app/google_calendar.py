"""
Google Calendar OAuth 2.0 integration.
Fetches events and converts them to Schedule objects.
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from schema import Schedule

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
TOKEN_PATH = Path(__file__).resolve().parents[1] / "data" / "google_token.json"

KST = timezone(timedelta(hours=9))


def get_auth_url(credentials_json: str) -> tuple[Any, str]:
    """
    Given credentials JSON string, return (flow, auth_url).
    The user must open auth_url, grant access, and paste the resulting code.
    """
    from google_auth_oauthlib.flow import Flow

    creds_dict = json.loads(credentials_json)
    flow = Flow.from_client_config(
        creds_dict,
        scopes=SCOPES,
        redirect_uri="urn:ietf:wg:oauth:2.0:oob",
    )
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return flow, auth_url


def exchange_code(flow: Any, code: str) -> dict:
    """Exchange auth code for token dict."""
    flow.fetch_token(code=code.strip())
    creds = flow.credentials
    token = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else [],
    }
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(json.dumps(token, ensure_ascii=False), encoding="utf-8")
    return token


def load_saved_token() -> dict | None:
    if TOKEN_PATH.exists():
        return json.loads(TOKEN_PATH.read_text(encoding="utf-8"))
    return None


def delete_saved_token() -> None:
    if TOKEN_PATH.exists():
        TOKEN_PATH.unlink()


def _build_service(token: dict):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=token.get("token"),
        refresh_token=token.get("refresh_token"),
        token_uri=token.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=token.get("client_id"),
        client_secret=token.get("client_secret"),
        scopes=token.get("scopes", SCOPES),
    )
    return build("calendar", "v3", credentials=creds)


def list_calendars(token: dict) -> list[dict]:
    svc = _build_service(token)
    result = svc.calendarList().list().execute()
    return [
        {"id": c["id"], "name": c.get("summary", c["id"])}
        for c in result.get("items", [])
    ]


def fetch_events(token: dict, calendar_id: str, target_date: date) -> list[Schedule]:
    """
    Fetch all events for target_date from the given calendar.
    Returns list of Schedule objects.
    """
    svc = _build_service(token)

    day_start = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, tzinfo=KST)
    day_end = day_start + timedelta(days=1)

    events_result = svc.events().list(
        calendarId=calendar_id,
        timeMin=day_start.isoformat(),
        timeMax=day_end.isoformat(),
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    schedules: list[Schedule] = []
    for i, ev in enumerate(events_result.get("items", [])):
        start_raw = ev.get("start", {})
        end_raw = ev.get("end", {})

        # Skip all-day events (no dateTime field)
        if "dateTime" not in start_raw:
            continue

        start_dt = _parse_dt(start_raw["dateTime"])
        end_dt = _parse_dt(end_raw["dateTime"])
        if end_dt <= start_dt:
            continue

        category = _infer_category(ev)
        location = ev.get("location") or _infer_location(ev)

        schedules.append(Schedule(
            id=f"gcal-{i:03d}",
            title=ev.get("summary", "제목 없음"),
            category=category,
            start=start_dt,
            end=end_dt,
            location=location,
            notes=_strip_html(ev.get("description", "")) or None,
        ))

    return schedules


def _parse_dt(dt_str: str) -> datetime:
    """Parse ISO 8601 datetime string to naive datetime in KST."""
    dt = datetime.fromisoformat(dt_str)
    if dt.tzinfo is not None:
        dt = dt.astimezone(KST).replace(tzinfo=None)
    return dt


CATEGORY_KEYWORDS: list[tuple[list[str], str]] = [
    (["회의", "미팅", "meeting", "sync", "call", "zoom", "meet"], "회의"),
    (["고객", "client", "customer", "interview", "인터뷰"], "고객"),
    (["학습", "study", "리딩", "reading", "세미나", "seminar", "강의"], "학습"),
    (["운동", "gym", "헬스", "yoga", "필라테스", "pilates", "러닝", "running"], "건강"),
    (["점심", "저녁", "식사", "lunch", "dinner", "밥"], "개인"),
    (["가족", "family", "아이", "kid", "부모", "parent"], "가족"),
    (["네트워킹", "network", "커피챗", "coffee chat", "멘토", "mentor"], "네트워킹"),
]


def _infer_category(ev: dict) -> str:
    text = (ev.get("summary", "") + " " + ev.get("description", "")).lower()
    for keywords, category in CATEGORY_KEYWORDS:
        if any(kw in text for kw in keywords):
            return category
    return "업무"


def _infer_location(ev: dict) -> str | None:
    text = (ev.get("summary", "") + " " + ev.get("description", "")).lower()
    if any(kw in text for kw in ["zoom", "줌"]):
        return "줌"
    if any(kw in text for kw in ["google meet", "meet.google", "미트"]):
        return "구글 미트"
    if any(kw in text for kw in ["teams", "팀즈"]):
        return "MS Teams"
    return None


def _strip_html(text: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", text).strip()
