import os
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from app_logging import setup_logging
from src.chat.models import Room, ChatMode
from src.services.wandb_service import init_wandb
from src.chat.conversation_service import ConversationService
from src.services.vllm_service import llm

os.environ["TOKENIZERS_PARALLELISM"] = "false"

setup_logging()
logger = logging.getLogger(__name__)

model_name_from_vllm = "unknown_model"

try:
    if hasattr(llm, "llm_engine") and hasattr(llm.llm_engine, "model_config"):
        model_name_from_vllm = llm.llm_engine.model_config.model
    elif hasattr(
        llm, "model_config"
    ):  # Fallback for simpler vLLM wrappers or future changes
        model_name_from_vllm = llm.model_config.model
except AttributeError:
    print("Could not retrieve model name from vLLM object for W&B config.")

wandb_config = {
    "model_name": model_name_from_vllm,
}
init_wandb(project_name="mm-chat-comparison", config=wandb_config)

app = FastAPI()
conversation_service = ConversationService()

current_file_dir = os.path.dirname(os.path.abspath(__file__))
static_files_dir = os.path.join(current_file_dir, "interface")
index_html_path = os.path.join(static_files_dir, "index.html")


@app.post("/room/{mode}", response_model=Room, status_code=status.HTTP_201_CREATED)
def create_new_room(mode: ChatMode):
    try:
        room = conversation_service.create_room(mode)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail={"error": str(e), "status": "error"}
        ) from e

    return room


@app.get("/room/{mode}/{room_id}", response_model=None)
def get_room_page() -> FileResponse | HTMLResponse:
    if os.path.exists(index_html_path):
        return FileResponse(index_html_path, media_type="text/html")
    else:
        return HTMLResponse(
            content="<html><head><title>Not Found</title></head><body><h1>Index.html not found</h1></body></html>",
            status_code=404,
        )


# This endpoint is used for both - single and comparison mode
# In comparison mode 2 separate connections are opened
@app.websocket("/ws/room/{mode}/{room_id}/{conversation_id}")
async def update_conversation(
    websocket: WebSocket, mode: ChatMode, room_id: str, conversation_id: str
):
    """Update conversation based on mode (single or comparison)"""
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_text()
            active_room = conversation_service.get_active_room(room_id=room_id)
            conversation = conversation_service.get_conversation(
                active_room.conversations, conversation_id
            )
            llm_response = None

            if mode == ChatMode.SINGLE_MODE:
                llm_response = conversation_service.get_response_sm(
                    conversation=conversation, prompt=data
                )
            else:
                llm_response = await conversation_service.get_response_cm(
                    conversation=conversation, prompt=data
                )

            response_data = {
                "conversation_id": conversation_id,
                "response": llm_response,
            }
            await websocket.send_json(response_data)

    except WebSocketDisconnect:
        logger.error("Client disconnected")
    except Exception as e:
        logger.error("Error: %s", e)
        await websocket.close(code=1011)


app.mount("/", StaticFiles(directory=static_files_dir, html=True), name="static")
