import uuid
from enum import Enum
from typing import List, Literal
from datetime import datetime
from pydantic import BaseModel, Field
from config import config

class Message(BaseModel):
    """Represents a message in the conversation with LLM."""
    role: str
    content: str
    # timestamp: datetime # Example if you add timestamp

class Conversation(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    model: Literal[config.MODEL1, config.MODEL2] = Field(default=config.MODEL1)
    messages: List[Message] = Field(default_factory=list)
    createdAt: datetime = Field(default_factory=datetime.now)

class ChatMode(Enum):
    """
    Distinguishes between two application modes: 
        single - uses one model
        comparison - uses 2 models(bigger and smaller) and generates two separate results in parallel
    """
    SINGLE_MODE = 'sm'
    COMPARISON_MODE = 'cm'

class Role(Enum):
    """Conversation roles enum"""
    USER = 'user'
    ASSISTANT = 'assistant'

class Room(BaseModel):
    """
    A Room class that is used to create  a new Room object when a user starts new chat.
    Chat includes 2 models therefore handles the same number of conversations
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    conversations: List[Conversation] = Field(default_factory=list)
