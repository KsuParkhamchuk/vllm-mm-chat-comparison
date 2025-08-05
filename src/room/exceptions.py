from enum import Enum


class ErrorMessages(Enum):
    SM_MODE_CONFIG_ERROR = "Model is not configured"
    CM_MODE_CONFIG_ERROR = "One of the models is not configured"
    LLM_ERROR_RESPONSE = "Sorry, I couldn't generate a response at the moment."


class NotFoundError(Exception):
    def __init__(self, obj, field, value, message=None):
        self.obj = obj
        self.field = field
        self.value = value

        if message is None:
            message = f"{obj} with {field}={value} not found"

        super().__init__(message)
