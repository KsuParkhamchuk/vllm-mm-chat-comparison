import uuid
import logging
from typing import List
from models.conversation import Conversation
from models.message import Message
from data.converations import conversations
from .vllm_service import generate_response
from .wandb_service import log_vllm_request_output_metrics 


logger = logging.getLogger(__name__)

def create_conversation():
    """ Create new conversation object"""
    conversation = Conversation()
    conversations.append(conversation)
    return conversation.id

def get_current_conversation(conversation_id: uuid.UUID) -> List[Message]:
    """ Return current active conversation """
    conversation_obj = next(conv for conv in conversations if conv.id == conversation_id)
    return conversation_obj.conversation

def message_constructor(role: str, content: str) -> Message:
    """ Return appropriate Message object for conversation format"""
    return {"role": role, "content": content}

def upd_conversation(conversation_id: uuid.UUID, role: str, content: str):
    """Update conversation object with new messages from user and LLM outputs"""
    conversation = get_current_conversation(conversation_id)
    usr_message = message_constructor(role, content)
    conversation.append(usr_message)

    request_outputs, manual_duration_sec = generate_response(conversation)

    if not request_outputs or not request_outputs[0].outputs:
        logger.error("LLM did not return a valid response or response was empty.")
        llm_message = message_constructor("assistant", "Sorry, I couldn't generate a response at the moment.")
        conversation.append(llm_message)
        return llm_message

    first_result = request_outputs[0] 
    llm_generated_text = first_result.outputs[0].text

    log_vllm_request_output_metrics(first_result, manual_duration_sec=manual_duration_sec)

    llm_message = message_constructor("assistant", llm_generated_text)
    conversation.append(llm_message)

    return llm_message
