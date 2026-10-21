from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from .models import VoteStatus

# --- Input Schemas ---
class TimeOptionCreate(BaseModel):
    start_time: datetime
    end_time: datetime

class EventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    time_options: List[TimeOptionCreate]

class SingleVoteInput(BaseModel):
    time_option_id: int
    status: VoteStatus

class ParticipantVoteCreate(BaseModel):
    participant_name: str
    votes: List[SingleVoteInput]

# --- Output Schemas ---
class VoteResponse(BaseModel):
    id: int
    participant_name: str
    status: VoteStatus

    class Config:
        from_attributes = True

class TimeOptionResponse(BaseModel):
    id: int
    start_time: datetime
    end_time: datetime
    votes: List[VoteResponse] = []
    is_busy: bool = False  # Beregnes dynamisk ud fra deltagerens kalender

    class Config:
        from_attributes = True

class EventResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    public_token: str
    time_options: List[TimeOptionResponse]

    class Config:
        from_attributes = True

class EventCreatedResponse(EventResponse):
    admin_token: str  # Returneres kun ved oprettelse