from models.conversation import Conversation
from models.message import Message
from data.converations import conversations
from .vllm_service import generate_response
import uuid
from .wandb_service import log_vllm_request_output_metrics 
import logging

logger = logging.getLogger(__name__)

def create_conversation():
    conversation = Conversation()
    conversations.append(conversation)
    return conversation.id

def upd_conversation(conversation_id: uuid.UUID, role: str, content: str):
    conversation_obj = next(conv for conv in conversations if conv.id == conversation_id)
    usr_message: Message = {"role": role, "content": content}
    append_message(conversation_id=conversation_id, message=usr_message)

    request_outputs, manual_duration_sec = generate_response(conversation_obj.conversation)

    if not request_outputs or not request_outputs[0].outputs:
        logger.error("LLM did not return a valid response or response was empty.")
        llm_message: Message = {"role": "assistant", "content": "Sorry, I couldn't generate a response at the moment."}
        append_message(conversation_id=conversation_id, message=llm_message)
        return llm_message

    first_result = request_outputs[0] 
    llm_generated_text = first_result.outputs[0].text

    log_vllm_request_output_metrics(first_result, manual_duration_sec=manual_duration_sec)

    llm_message: Message = {"role": "assistant", "content": llm_generated_text}
    append_message(conversation_id=conversation_id, message=llm_message)

    return llm_message

def append_message(conversation_id: uuid.UUID, message: Message):
    conversation_obj = next(conv for conv in conversations if conv.id == conversation_id)
    conversation_obj.conversation.append(message)