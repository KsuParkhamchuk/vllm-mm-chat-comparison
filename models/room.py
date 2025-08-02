from typing import List
import uuid
from pydantic import BaseModel, Field
from models.conversation import Conversation


class Room(BaseModel):
    """
    A Room class that is used to create  a new Room object when a user starts new chat.
    Chat includes 2 models therefore handles the same number of conversations
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4())
    conversations: List[Conversation] = Field(default_factory=list)
