import os
import urllib.parse
import httpx
from fastapi.responses import FileResponse, RedirectResponse
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional
from . import models, schemas, services
from .database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Smart Aftale App API")

# Tillad forbindelse mellem frontend og backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GOOGLE_CLIENT_ID = "671036601492-sakumm688rpi0786e9pqe6jjf9e5mpc0.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "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"
GOOGLE_REDIRECT_URI = "http://localhost:8000/auth/google/callback"

@app.get("/auth/google/login")
def google_login(event_token: str = ""):
    """Sender brugeren videre til Googles login-skærm (kun med read-only freebusy adgang)."""
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        # Vi beder KUN om lov til at læse ledig/optaget-status, intet andet!
        "scope": "https://www.googleapis.com/auth/calendar.freebusy",
        "access_type": "online",
        "state": event_token,  # Husker hvilken aftale brugeren kom fra
        "prompt": "consent"
    }
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url)

@app.get("/auth/google/callback")
async def google_callback(code: str, state: str = ""):
    """Modtager koden fra Google, veksler den til et access_token og sender brugeren tilbage til aftalen."""
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(token_url, data=data)
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Kunne ikke hente token fra Google")
        token_data = resp.json()
        access_token = token_data.get("access_token")

    # Send brugeren tilbage til forsiden med både aftale-token og kalender-token
    redirect_url = f"/?token={state}&google_token={access_token}" if state else f"/?google_token={access_token}"
    return RedirectResponse(redirect_url)
# NYT: Når du åbner http://localhost:8000 i browseren, vises index.html!
@app.get("/")
def serve_frontend():
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    return FileResponse(html_path)

@app.post("/events/", response_model=schemas.EventCreatedResponse)
def create_event(event_data: schemas.EventCreate, db: Session = Depends(get_db)):
    new_event = models.Event(
        title=event_data.title,
        description=event_data.description
    )
    db.add(new_event)
    db.flush()  # Henter new_event.id før commit

    for option in event_data.time_options:
        db_option = models.TimeOption(
            event_id=new_event.id,
            start_time=option.start_time,
            end_time=option.end_time
        )
        db.add(db_option)

    db.commit()
    db.refresh(new_event)
    return new_event

@app.get("/events/{public_token}", response_model=schemas.EventResponse)
async def get_event(
    public_token: str,
    db: Session = Depends(get_db),
    x_calendar_token: Optional[str] = Header(None, description="Valgfri Google OAuth access token")
):
    event = db.query(models.Event).filter(models.Event.public_token == public_token).first()
    if not event:
        raise HTTPException(status_code=404, detail="Aftalen blev ikke fundet")

    # Konverter til Pydantic-model så vi kan berige med 'is_busy'
    response_data = schemas.EventResponse.model_validate(event)

    # Hvis brugeren har koblet sin kalender på, tjekkes 'freeBusy'
    if x_calendar_token and response_data.time_options:
        min_time = min(opt.start_time for opt in response_data.time_options)
        max_time = max(opt.end_time for opt in response_data.time_options)
        
        busy_slots = await services.get_google_busy_times(x_calendar_token, min_time, max_time)
        
        for option in response_data.time_options:
            option.is_busy = services.check_is_busy(option.start_time, option.end_time, busy_slots)

    return response_data

@app.post("/events/{public_token}/vote")
def submit_votes(
    public_token: str, 
    vote_data: schemas.ParticipantVoteCreate, 
    db: Session = Depends(get_db)
):
    event = db.query(models.Event).filter(models.Event.public_token == public_token).first()
    if not event:
        raise HTTPException(status_code=404, detail="Aftalen blev ikke fundet")

    valid_option_ids = {opt.id for opt in event.time_options}

    for vote in vote_data.votes:
        if vote.time_option_id not in valid_option_ids:
            raise HTTPException(status_code=400, detail=f"Ugyldigt tidspunkt ID: {vote.time_option_id}")
        
        db_vote = models.Vote(
            time_option_id=vote.time_option_id,
            participant_name=vote_data.participant_name,
            status=vote.status
        )
        db.add(db_vote)

    db.commit()
    return {"message": "Stemmer registreret succesfuldt"}