from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional
from . import models, schemas, services
from .database import engine, get_db

# Opretter tabellerne i PostgreSQL ved opstart
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Smart Aftale App API")

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