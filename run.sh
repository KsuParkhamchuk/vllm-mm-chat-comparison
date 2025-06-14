#!/bin/bash

VENV_DIR=".venv"
HOST="0.0.0.0"
PORT="8002"

# Ray setup for distributed model serving
RAY_PORT="6379"
HEAD_NODE="localhost" # e.g., "192.168.1.100"
WORKER_NODE="localhost" # e.g., "192.168.1.101"


# Start virtual environment
echo "Starting the application"

if [ ! -d "$VENV_DIR" ]; then
echo "Virtual environment not found. Creating one..."
    python -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"

    echo "Installing the dependencies"
    pip install -r requirements.txt
else
    echo "Activating virtual environment"
    source "$VENV_DIR/bin/activate"
fi


# Run Ray nodes on remote machines
# echo "Starting head node on $HEAD_NODE"
# ssh $HEAD_NODE "ray start --head --port=$RAY_PORT"

# echo "Starting worker node on $WORKER_NODE"
# ssh $WORKER_NODE "ray start --address=$HEAD_NODE:$RAY_PORT"ok

if [ -f .env ]; then
    echo "Loading environment variables from .env file"
    export $(grep -v '^#' .env | xargs)
fi

# Starting main application
echo "Starting FastAPI application"
uvicorn main:app --host $HOST --port $PORT --reload &
MAIN_PID=$!
echo "FastAPI application started with PID: $MAIN_PID"

echo "Serving chat models on dedicated servers"
scp -i ~/.ssh/vastai -P $REMOTE_PORT_1 ./serve_sm.sh ./.env root@$REMOTE_HOST_1:/workspace/
ssh -i ~/.ssh/vastai -p $REMOTE_PORT_1 root@$REMOTE_HOST_1 -L $PORT_1:localhost:$PORT_1 -N &
ssh -i ~/.ssh/vastai -p $REMOTE_PORT_1 root@$REMOTE_HOST_1 "cd /workspace && chmod +x serve_sm.sh && ./serve_sm.sh" > sm_server.log 2>&1 &
MODEL1_PID=$!

echo "Copy script and run server"

# export RAY_ADDRESS="$HEAD_NODE:$RAY_PORT"
scp -i $SSH_KEY_PATH -P $REMOTE_PORT_2 ./serve_lg.sh ./.env root@$REMOTE_HOST_2:/workspace/
ssh -i $SSH_KEY_PATH -p $REMOTE_PORT_2 root@$REMOTE_HOST_2 -L $PORT_2:localhost:$PORT_2 -N &
ssh -i $SSH_KEY_PATH -p $REMOTE_PORT_2 root@$REMOTE_HOST_2 "cd /workspace && chmod +x serve_lg.sh && ./serve_lg.sh" > lg_server.log 2>&1 &
MODEL2_PID=$!


cleanup() {
    echo "Stopping all services..."
    kill $MAIN_PID 2>/dev/null
    kill $MODEL1_PID 2>/dev/null
    kill $MODEL2_PID 2>/dev/null
    ssh -i $SSH_KEY_PATH -p $REMOTE_PORT_1 root@$REMOTE_HOST_1 "pkill -f 'vllm serve'"
    ssh -i $SSH_KEY_PATH -p $REMOTE_PORT_2 root@$REMOTE_HOST_2 "pkill -f 'vllm serve'"
    
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