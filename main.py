import os
import uuid
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from services.wandb_service import init_wandb
from services.conversation_service import create_room, get_response_cm, get_response_sm
from fastapi.staticfiles import StaticFiles
from services.vllm_service import llm
from models.mode import ChatMode

os.environ["TOKENIZERS_PARALLELISM"] = "false"

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

current_file_dir = os.path.dirname(os.path.abspath(__file__))
static_files_dir = os.path.join(current_file_dir, "interface")
index_html_path = os.path.join(static_files_dir, "index.html")


@app.post("/room/{mode}")
def create_new_room(mode: ChatMode):
    try:
        room = create_room(mode)
    except Exception as e:
        return {"error": str(e)}

    return room


@app.get("/room/{mode}/{room_id}")
def get_room_page(mode: ChatMode, room_id: str):
    if os.path.exists(index_html_path):
        return FileResponse(index_html_path, media_type="text/html")
    else:
        return HTMLResponse(
            content="<html><head><title>Not Found</title></head><body><h1>Index.html not found</h1></body></html>",
            status_code=404,
        )


# sm - single mode (one model used)
@app.websocket("/ws/room/{mode}/{room_id}/{conversation_id}")
async def update_conversation(
    websocket: WebSocket, mode: ChatMode, room_id: str, conversation_id: str
):
    """Update conversation based on mode (single or comparison)"""
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_text()
            llm_response = None

            if mode == ChatMode.SINGLE_MODE:
                llm_response = get_response_sm(
                    room_id=uuid.UUID(room_id),
                    conversation_id=uuid.UUID(conversation_id),
                    prompt=data,
                )
            else:
                llm_response = await get_response_cm(
                    room_id=uuid.UUID(room_id),
                    conversation_id=uuid.UUID(conversation_id),
                    prompt=data,
                )

            response_data = {
                "conversation_id": conversation_id,
                "response": llm_response,
            }
            await websocket.send_json(response_data)

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error: {e}")
        await websocket.close(code=1011)


app.mount("/", StaticFiles(directory=static_files_dir, html=True), name="static")
