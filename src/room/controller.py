import logging
from pathlib import Path
from fastapi import (
    APIRouter,
    Depends,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
    status,
)
from fastapi.responses import HTMLResponse, FileResponse
from src.room.models import Room, ChatMode
from src.room.room_service import RoomService

logger = logging.getLogger(__name__)

index_html_path = Path(__file__).resolve().parent.parent.parent / "interface/index.html"


def get_conversation_service():
    return RoomService()


def get_room():
    return Room()


router = APIRouter(prefix="/room")


@router.post("/{mode}", response_model=Room, status_code=status.HTTP_201_CREATED)
def create_new_room(
    mode: ChatMode,
    conversation_service: RoomService = Depends(get_conversation_service),
    room: Room = Depends(get_room),
):
    try:
        room = conversation_service.create_room(mode, room)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail={"error": str(e), "status": "error"}
        ) from e

    return room


@router.get("/{mode}/{room_id}", response_model=None)
def get_room_page() -> FileResponse | HTMLResponse:
    if Path.exists(index_html_path):
        return FileResponse(index_html_path, media_type="text/html")
    else:
        return HTMLResponse(
            content="<html><head><title>Not Found</title></head><body><h1>Index.html not found</h1></body></html>",
            status_code=404,
        )


# This endpoint is used for both - single and comparison mode
# In comparison mode 2 separate connections are opened
@router.websocket("/ws/{mode}/{room_id}/{conversation_id}")
async def update_conversation(
    websocket: WebSocket,
    mode: ChatMode,
    room_id: str,
    conversation_id: str,
    conversation_service: RoomService = Depends(get_conversation_service),
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
