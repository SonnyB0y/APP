import secrets
import enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from .database import Base

class VoteStatus(str, enum.Enum):
    YES = "yes"
    NO = "no"
    IF_NEED_BE = "if_need_be"

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    public_token = Column(String, unique=True, index=True, default=lambda: secrets.token_urlsafe(8))
    admin_token = Column(String, unique=True, index=True, default=lambda: secrets.token_urlsafe(12))

    time_options = relationship("TimeOption", back_populates="event", cascade="all, delete-orphan")

class TimeOption(Base):
    __tablename__ = "time_options"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)

    event = relationship("Event", back_populates="time_options")
    votes = relationship("Vote", back_populates="time_option", cascade="all, delete-orphan")

class Vote(Base):
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True, index=True)
    time_option_id = Column(Integer, ForeignKey("time_options.id"), nullable=False)
    participant_name = Column(String, nullable=False)
    status = Column(Enum(VoteStatus), nullable=False)

    time_option = relationship("TimeOption", back_populates="votes")