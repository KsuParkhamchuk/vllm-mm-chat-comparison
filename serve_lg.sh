echo "Loading env variables"

if [ -f .env ]; then
    echo "Loading environment variables from .env file"
    export $(grep -v '^#' .env | xargs)
fi

echo "Installing dependencies for starting vllm server"

pip install vllm
# huggingface-cli login

# # if model is quantized
pip install bitsandbytes 

echo "Running vllm server with custom parameters"
# max-model-len - context window
# max-seq-len - maximum number of concurrent sequences
# tensor-parallel-size - model inference distribution across available gpus 
vllm serve $MODEL_2 --port $PORT_2 --tensor-parallel-size 2 --quantization bitsandbytes --max-model-len $MAX_MODEL_LEN --max-seq-len $MAX_NUM_SEQ --host 0.0.0.0