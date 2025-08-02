echo "Loading env variables"

if [ -f .env ]; then
    echo "Loading environment variables from .env file"
    export $(grep -v '^#' .env | xargs)
fi

echo "Installing dependencies for starting vllm server"

echo "Start virtual environment"

if [ ! -d "$VENV_DIR" ]; then
echo "Virtual environment not found. Creating one..."
    python -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    pip install vllm
    huggingface-cli login
else
    echo "Activating virtual environment"
    source "$VENV_DIR/bin/activate"
fi


echo "Running vllm server with custom parameters"

vllm serve $MODEL1 --port $PORT_1 --host 0.0.0.0