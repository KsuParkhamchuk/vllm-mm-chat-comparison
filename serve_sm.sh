echo "Loading env variables"

if [ -f .env ]; then
    echo "Loading environment variables from .env file"
    export $(grep -v '^#' .env | xargs)
fi

echo "Installing dependencies for starting vllm server"

pip install vllm
huggingface-cli login

echo "Running vllm server with custom parameters"

vllm serve $MODEL_1 --port $PORT_1 --host 0.0.0.0