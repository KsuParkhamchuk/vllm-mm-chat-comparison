from typing_extensions import TypedDict
# from datetime import datetime # Only if you re-add timestamp

class Message(TypedDict):
    """Represents a message in the conversation."""
    role: str
    content: str
    # timestamp: datetime # Example if you add timestamp