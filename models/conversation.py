import uuid
from typing import List, Literal
from datetime import datetime
from pydantic import BaseModel, Field
from config import config
from .message import Message

class Conversation(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4())
    model: Literal[config.MODEL1, config.MODEL2] = Field(default=config.MODEL1)
    messages: List[Message] = Field(default_factory=list)
    createdAt: datetime = Field(default_factory=datetime.now())
