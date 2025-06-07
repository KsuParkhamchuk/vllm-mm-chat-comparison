import time
from vllm import LLM, SamplingParams
from vllm.config import CompilationConfig

sampling_params = SamplingParams(temperature=0.8, max_tokens=200)
# TODO: test with LLM gpu optimization params and compilation config
compilation_config = CompilationConfig(level=2)

llm = LLM(model="google/gemma-3-1b-it")

def generate_response(conversation):
    """Generates a response using vLLM."""
    start_time = time.monotonic()
    output = llm.chat(conversation, sampling_params=sampling_params)
    end_time = time.monotonic()
    duration_sec = end_time - start_time
    return output, duration_sec
