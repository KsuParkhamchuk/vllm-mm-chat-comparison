#!/bin/bash

VENV_DIR=".venv"
APP_FILE="main.py"
HOST="0.0.0.0"
PORT="8000"
MODEL_1="google/gemma-3-1b-it"
MODEL_2="google/gemma-3-1b-it"
PORT_1="8001"
PORT_2="8002"


# Ray setup for distributed model serving
RAY_PORT="6379"
HEAD_NODE="localhost" # e.g., "192.168.1.100"
WORKER_NODE="localhost" # e.g., "192.168.1.101"


# Start virtual environment
echo "Starting the application"

if [ ! -d "$VENV_DIR" ]; then
    echo "Activating virtual environment"
    source "$VENV_DIR/bin/activate"
else
    echo "Virtual environment not found. Creating one..."
    python -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"

    echo "Installing the dependencies"
    pip install -r requirements.txt
fi


# Run Ray nodes on remote machines
echo "Starting head node on $HEAD_NODE"
ssh $HEAD_NODE "ray start --head --port=$RAY_PORT"

echo "Starting worker node on $WORKER_NODE"
ssh $WORKER_NODE "ray start --address=$HEAD_NODE:$RAY_PORT"


echo "Serving chat models on dedicated servers"
vllm serve $MODEL_1 --port $PORT_1 &
MODEL1_PID=$!

# export RAY_ADDRESS="$HEAD_NODE:$RAY_PORT"
# vllm serve $MODEL_2 --port $PORT_2 --tensor-parallel-size 2 &
# MODEL2_PID=$!

# Starting main application
echo "Starting FastAPI application"
uvicorn main:app --host $HOST --port $PORT --reload &

cleanup() {
    echo "Stopping all services..."
    kill $MAIN_PID 2>/dev/null
    kill $MODEL1_PID 2>/dev/null
    kill $MODEL2_PID 2>/dev/null
    
    # Stop Ray cluster
    if [ "$HEAD_NODE" = "localhost" ]; then
        echo "Stopping local Ray cluster"
        ray stop
    else
        echo "Stopping Ray worker node"
        ssh $WORKER_NODE "ray stop"
        echo "Stopping Ray head node"
        ssh $HEAD_NODE "ray stop"
    fi
    
    echo "Deactivating virtual environment..."
    deactivate
    exit 0
}

trap cleanup SIGINT SIGTERM

wait