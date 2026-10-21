import httpx
from datetime import datetime
from typing import List, Tuple

async def get_google_busy_times(
    access_token: str, time_min: datetime, time_max: datetime
) -> List[Tuple[datetime, datetime]]:
    """Henter optagede tidsrum fra brugerens primære Google Kalender."""
    url = "https://www.googleapis.com/calendar/v3/freeBusy"
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {
        "timeMin": time_min.isoformat(),
        "timeMax": time_max.isoformat(),
        "items": [{"id": "primary"}]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            return []  # Fejler stille hvis token er udløbet/ugyldigt
        
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
    for busy_start, busy_end in busy_slots:
        # Matematisk tjek for om to tidsintervaller overlapper
        if max(option_start, busy_start) < min(option_end, busy_end):
            return True
    return False