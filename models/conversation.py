import uuid
from typing import List
from datetime import datetime
from pydantic import BaseModel, Field
from .message import Message

class Conversation(BaseModel):
    id: uuid.UUID = Field(default_factory=lambda: uuid.uuid4())
    model: str = Field(default="Some model")
    conversation: List[Message] = []
    createdAt: datetime = Field(default_factory=lambda: datetime.now)

    