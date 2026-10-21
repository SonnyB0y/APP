import httpx
from datetime import datetime, timezone
from typing import List, Tuple

def to_utc_iso(dt: datetime) -> str:
    """Sikrer at datoen er i UTC og slutter på 'Z', som Google Calendar API kræver."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

async def get_google_busy_times(
    access_token: str, time_min: datetime, time_max: datetime
) -> List[Tuple[datetime, datetime]]:
    """Henter optagede tidsrum fra brugerens primære Google Kalender."""
    url = "https://www.googleapis.com/calendar/v3/freeBusy"
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {
        "timeMin": to_utc_iso(time_min),
        "timeMax": to_utc_iso(time_max),
        "items": [{"id": "primary"}]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        print("🔍 GOOGLE FREEBUSY STATUS:", response.status_code)
        print("🔍 GOOGLE FREEBUSY SVAR:", response.text)

        if response.status_code != 200:
            return []
        
        data = response.json()
        busy_list = data.get("calendars", {}).get("primary", {}).get("busy", [])
        
        parsed_busy = []
        for slot in busy_list:
            start = datetime.fromisoformat(slot["start"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(slot["end"].replace("Z", "+00:00"))
            parsed_busy.append((start, end))
            
        return parsed_busy

def check_is_busy(
    option_start: datetime, option_end: datetime, busy_slots: List[Tuple[datetime, datetime]]
) -> bool:
    """Returnerer True hvis tidsmuligheden overlapper med en optaget kalenderblok."""
    opt_start_utc = option_start.astimezone(timezone.utc) if option_start.tzinfo else option_start.replace(tzinfo=timezone.utc)
    opt_end_utc = option_end.astimezone(timezone.utc) if option_end.tzinfo else option_end.replace(tzinfo=timezone.utc)

    for busy_start, busy_end in busy_slots:
        if max(opt_start_utc, busy_start) < min(opt_end_utc, busy_end):
            return True
    return False