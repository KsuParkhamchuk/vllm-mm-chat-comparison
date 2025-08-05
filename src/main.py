import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from src.app_logging import setup_logging
from src.services.wandb_service import init_wandb
from src.services.vllm_service import llm
from src.rate_limiting import limiter
from src.room import controller as room_controller

os.environ["TOKENIZERS_PARALLELISM"] = "false"

setup_logging()

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

project_root = Path(__file__).resolve().parent.parent
static_files_dir = project_root / "interface"


app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.include_router(room_controller.router)

app.mount("/", StaticFiles(directory=static_files_dir, html=True), name="static")
