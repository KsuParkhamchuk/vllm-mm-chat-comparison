import uuid
import logging
from typing import List
import httpx
from src.config import config
from src.data.rooms import rooms
from src.services.vllm_service import VLLMService
from src.services.wandb_service import log_vllm_request_output_metrics
from .models import Conversation, Message, Role, Room, ChatMode
from .exceptions import NotFoundError, ErrorMessages


logger = logging.getLogger(__name__)
vllm_service = VLLMService()


class RoomService:

    def create_room(self, mode: ChatMode, room=Room):
        """Create new room object"""

        if ChatMode.SINGLE_MODE and not config.MODEL1:
            raise ValueError(ErrorMessages.SM_MODE_CONFIG_ERROR)

        if ChatMode.COMPARISON_MODE and not (config.MODEL1 or config.MODEL2):
            raise ValueError(ErrorMessages.CM_MODE_CONFIG_ERROR)

        if mode == ChatMode.SINGLE_MODE:
            room.conversations = [Conversation(model=config.MODEL1)]
        else:
            room.conversations = [
                Conversation(model=config.MODEL1),
                Conversation(model=config.MODEL2),
            ]

        rooms.append(room)

        return room

    def get_active_room(self, room_id: uuid.UUID) -> Room:
        """Return current active room"""

        room_obj = next((room for room in rooms if str(room.id) == room_id), None)

        if room_obj is None:
            raise NotFoundError("Room", "id", room_id)

        return room_obj

    def get_conversation(
        self, conversations, conversation_id: uuid.UUID
    ) -> List[List[Message]]:
        """Return current active conversation"""

        conversation = next(
            (conv for conv in conversations if str(conv.id) == conversation_id), None
        )

        if conversation is None:
            raise NotFoundError("Conversation", "id", conversation_id)

        return conversation

    def message_constructor(self, role: Role, content: str) -> Message:
        """Return appropriate Message object for conversation format"""

        return {"role": role, "content": content}

    def update_conversation(
        self,
        conversation: Conversation,
        role: Role,
        content: str,
    ) -> List[Message]:
        """Update conversation object with new messages from user and LLM outputs"""

        message = self.message_constructor(role, content)
        conversation.messages.append(message)

        return conversation.messages

    def get_response_sm(self, conversation: Conversation, prompt: str) -> str:
        """
        Update conversation object with new messages from user and LLM outputs in a single mode
        Single mode generate LLM responses directly using LLM class (from vllm lib)
        Using LLM class directly allows avoid network overhead, simpler setup.
        Good for small models

        Args:
            conversation: Conversation object containing information about a particular conversation
            prompt: User prompt to the model

        Returns:
            str: string that contains the LLM response or error message
        """

        # Add user message to the conversation
        messages = self.update_conversation(
            conversation=conversation, role=Role.USER.value, content=prompt
        )

        request_outputs, manual_duration_sec = vllm_service.generate_response(messages)

        if not request_outputs or not request_outputs[0].outputs:
            logger.error("LLM did not return a valid response or response was empty.")
            llm_error_response = ErrorMessages.LLM_ERROR_RESPONSE

            # Add error response to the conversation
            self.update_conversation(
                conversation=conversation,
                role=Role.ASSISTANT.value,
                content=llm_error_response,
            )

            return llm_error_response

        first_result = request_outputs[0]
        llm_generated_text = first_result.outputs[0].text

        log_vllm_request_output_metrics(
            first_result, manual_duration_sec=manual_duration_sec
        )

        # Add assistant response to the conversation
        self.update_conversation(
            conversation=conversation,
            role=Role.ASSISTANT.value,
            content=llm_generated_text,
        )

        return llm_generated_text

    async def make_model_request(self, messages: List[Message], model: str):
        """
        Make an asynchronous HTTP request to a language model endpoint.

        Args:
            messages: List of Message objects containing the conversation history
            model: String identifier of the model to use (must match config.MODEL1 or config.MODEL2)

        Returns:
            dict: The JSON response from the model endpoint, or None if the request failed

        Raises:
            httpx.ConnectError: If connection to the endpoint fails
            httpx.ReadTimeout: If the request times out
            httpx.HTTPStatusError: If the server returns an error status code
        """
        endpoint = None

        if model == config.MODEL1:
            endpoint = config.MODEL1_ENDPOINT
        elif model == config.MODEL2:
            endpoint = config.MODEL2_ENDPOINT

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    endpoint,
                    json={"messages": messages, "temperature": 0.8, "max_tokens": 500},
                )

                if response.status_code != 200:
                    logger.error("Error response: %s", response.text)
                    return None

                return response.json()
        except httpx.ConnectError as e:
            logger.error("Connection error: %s - Could not connect to %s", e, endpoint)
            return None
        except httpx.ReadTimeout as e:
            logger.error("Timeout error: %s - Request to %s timed out", e, endpoint)
            return None
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error: %s", e)
            return None
        except Exception as e:
            logger.error("Error making model request: %s: %s", type(e).__name__, e)
            return None

    async def get_response_cm(self, conversation: Conversation, prompt: str) -> str:
        """
        Update conversation object with new messages from user and LLM outputs in a comparison mode
        Comparison mode generate LLM responses by making requests to separate vllm servers with different models
        Scalable approach that enables concurrency

        Args:
            conversation: Conversation object containing information about a particular conversation
            prompt: User prompt to the model

        Returns:
            str: string that contains the LLM response or error message
        """
        model = conversation.model
        messages = self.update_conversation(
            conversation=conversation, role=Role.USER.value, content=prompt
        )
        response = None

        response = await self.make_model_request(messages=messages, model=model)

        if not response:
            llm_error_response = ErrorMessages.LLM_ERROR_RESPONSE
            self.update_conversation(
                conversation=conversation,
                role=Role.ASSISTANT.value,
                content=llm_error_response,
            )
            return llm_error_response

        self.update_conversation(
            conversation=conversation,
            role=Role.ASSISTANT.value,
            content=response["choices"][0]["message"]["content"],
        )

        return response["choices"][0]["message"]["content"]
