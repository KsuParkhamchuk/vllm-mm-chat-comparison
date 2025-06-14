echo "Loading env variables"

if [ -f .env ]; then
    echo "Loading environment variables from .env file"
    export $(grep -v '^#' .env | xargs)
fi

echo "Start virtual environment"

if [ ! -d "$VENV_DIR" ]; then
echo "Virtual environment not found. Creating one..."
    python -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    pip install vllm
    # huggingface-cli login

    # if model is quantized
    pip install bitsandbytes 
else
    echo "Activating virtual environment"
    source "$VENV_DIR/bin/activate"
fi

export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

echo "Running vllm server with custom parameters"
# max-model-len - context window
# max-seq-len - maximum number of concurrent sequences
# tensor-parallel-size - model inference distribution across available gpus 
vllm serve $MODEL2 --port $PORT_2 --tensor-parallel-size 2 --quantization bitsandbytes --max-model-len $MAX_MODEL_LEN --max-num-seq $MAX_NUM_SEQ --host 0.0.0.0 --gpu-memory-utilization 0.7