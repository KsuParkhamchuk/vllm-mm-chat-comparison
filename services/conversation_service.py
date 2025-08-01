import uuid
import logging
from typing import List
import httpx
from models.conversation import Conversation
from models.message import Message
from models.mode import ChatMode
from models.role import Role
from models.room import Room
from data.rooms import rooms
from config import config
from .vllm_service import generate_response
from .wandb_service import log_vllm_request_output_metrics


logger = logging.getLogger(__name__)


def create_room(mode: ChatMode):
    """Create new room object"""

    if ChatMode.SINGLE_MODE and not config.MODEL1:
        raise ValueError("Model is not configured")

    if ChatMode.COMPARISON_MODE and not (config.MODEL1 or config.MODEL2):
        raise ValueError("One of the models is not configured")

    room = Room()

    if mode == ChatMode.SINGLE_MODE:
        room.conversations = [Conversation(model=config.MODEL1)]
    else:
        room.conversations = [
            Conversation(model=config.MODEL1),
            Conversation(model=config.MODEL2),
        ]

    rooms.append(room)

    return room


def get_active_room(room_id: uuid.UUID) -> Room:
    """Return current active room"""

    room_obj = next((room for room in rooms if room.id == room_id), None)

    if room_obj is None:
        raise ValueError(f"Room with ID={room_id} was not found")

    return room_obj


def get_conversation(conversations, conversation_id: uuid.UUID) -> List[List[Message]]:
    """Return current active conversations"""

    conversation = next((conv for conv in conversations if conv.id == conversation_id), None)

    if conversation is None:
        raise ValueError(f"Conversation with ID={conversation_id} was not found")

    return conversation


def message_constructor(role: Role, content: str) -> Message:
    """Return appropriate Message object for conversation format"""

    return {"role": role, "content": content}


def update_conversation(
    room_id: uuid.UUID,
    conversation_id: uuid.UUID,
    role: Role,
    content: str,
) -> List[Message]:
    """Update conversation object with new messages from user and LLM outputs"""

    active_room = get_active_room(room_id=room_id)
    conversation = get_conversation(active_room.conversations, conversation_id)

    message = message_constructor(role, content)
    conversation.messages.append(message)

    return conversation.messages


def get_response_sm(room_id: uuid.UUID, conversation_id: uuid.UUID, prompt: str) -> str:
    """Update conversation object with new messages from user and LLM outputs"""

    messages = update_conversation(
        room_id=room_id, conversation_id=conversation_id, role=Role.USER, content=prompt
    )

    request_outputs, manual_duration_sec = generate_response(messages)

    if not request_outputs or not request_outputs[0].outputs:
        logger.error("LLM did not return a valid response or response was empty.")
        llm_error_response = "Sorry, I couldn't generate a response at the moment."

        update_conversation(
            room_id=room_id,
            conversation_id=conversation_id,
            role=Role.ASSISTANT,
            content=llm_error_response,
        )

        return llm_error_response

    first_result = request_outputs[0]
    llm_generated_text = first_result.outputs[0].text

    log_vllm_request_output_metrics(
        first_result, manual_duration_sec=manual_duration_sec
    )

    update_conversation(
        room_id=room_id,
        conversation_id=conversation_id,
        role=Role.ASSISTANT,
        content=llm_generated_text,
    )

    return llm_generated_text


async def make_model_request(messages: List[Message], endpoint: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                endpoint,
                json={"messages": messages, "temperature": 0.8, "max_tokens": 500},
            )

            print(f"Response status: {response.status_code}")

            if response.status_code != 200:
                print(f"Error response: {response.text}")
                return None

            return response.json()
    except httpx.ConnectError as e:
        print(f"Connection error: {e} - Could not connect to {endpoint}")
        return None
    except httpx.ReadTimeout as e:
        print(f"Timeout error: {e} - Request to {endpoint} timed out")
        return None
    except httpx.HTTPStatusError as e:
        print(f"HTTP error: {e}")
        return None
    except Exception as e:
        print(f"Error making model request: {type(e).__name__}: {e}")
        return None


async def get_response_cm(
    room_id: uuid.UUID, conversation_id: uuid.UUID, prompt: str
) -> str:
    # TODO optimize room and conversation search
    active_room = get_active_room(room_id=room_id)
    conversation_model = get_conversation(
        active_room.conversations, conversation_id
    ).model
    messages = update_conversation(
        room_id=room_id, conversation_id=conversation_id, role=Role.USER, content=prompt
    )
    response = None

    if conversation_model == config.MODEL1:
        response = await make_model_request(
            messages=messages, endpoint=config.MODEL1_ENDPOINT
        )

    elif conversation_model == config.MODEL2:
        response = await make_model_request(
            messages=messages, endpoint=config.MODEL2_ENDPOINT
        )

    if not response:
        llm_error_response = "Sorry, I couldn't generate a response at the moment."
        update_conversation(
            room_id=room_id,
            conversation_id=conversation_id,
            role=Role.ASSISTANT,
            content=llm_error_response,
        )
        return llm_error_response

    update_conversation(
        room_id=room_id,
        conversation_id=conversation_id,
        role=Role.ASSISTANT,
        content=response["choices"][0]["message"]["content"],
    )

    return response["choices"][0]["message"]["content"]
