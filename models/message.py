"""Message class. """

from typing_extensions import TypedDict

class Message(TypedDict):
    """Represents a message in the conversation with LLM."""
    role: str
    content: str
    # timestamp: datetime # Example if you add timestamp