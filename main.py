from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from services.conversation_service import create_conversation, upd_conversation
from fastapi.staticfiles import StaticFiles
import os
import uuid
from services.wandb_service import init_wandb
from services.vllm_service import llm

os.environ["TOKENIZERS_PARALLELISM"] = "false"

model_name_from_vllm = "unknown_model"
try:
    if hasattr(llm, 'llm_engine') and hasattr(llm.llm_engine, 'model_config'):
        model_name_from_vllm = llm.llm_engine.model_config.model
    elif hasattr(llm, 'model_config'): # Fallback for simpler vLLM wrappers or future changes
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

@app.post("/conversation")
def create_new_conversation():
    try:
        id = create_conversation()
    except Exception as e:
        return {"error": str(e)}

    return {"conversation_id": id}

@app.get("/conversation/{conversation_id}")
def get_conversation_page(conversation_id: str):
    if os.path.exists(index_html_path):
        return FileResponse(index_html_path, media_type="text/html")
    else:
        return HTMLResponse(content="<html><head><title>Not Found</title></head><body><h1>Index.html not found</h1></body></html>", status_code=404)

@app.websocket("/ws/conversation/{conversation_id}")
async def update_conversation(websocket: WebSocket, conversation_id: str):
    await websocket.accept()

    try: 
        while True:
            data = await websocket.receive_text()
            llm_message = upd_conversation(uuid.UUID(conversation_id), "user", data)
            await websocket.send_text(llm_message['content'])
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error: {e}")
        await websocket.close(code=1011)
        

app.mount("/", StaticFiles(directory=static_files_dir, html=True), name="static")