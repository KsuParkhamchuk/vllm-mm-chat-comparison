import uuid
from typing import List, Literal
from datetime import datetime
from ..config import config
from pydantic import BaseModel, Field
from .message import Message

class Conversation(BaseModel):
    id: uuid.UUID = Field(default_factory=lambda: uuid.uuid4())
    model: Literal[config.MODEL1_NAME, config.MODEL2_NAME] = Field(default=config.MODEL1_NAME)
    messages: List[Message] = []
    createdAt: datetime = Field(default_factory=lambda: datetime.now)

    