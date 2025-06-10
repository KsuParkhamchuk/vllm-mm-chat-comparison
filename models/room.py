from typing import List
import uuid
from pydantic import BaseModel, Field
from models.conversation import Conversation

class Room(BaseModel):
    id: uuid.UUID = Field(default_factory=lambda: uuid.uuid4())
    conversations: List[Conversation] = Field(default=[])