import time
from vllm import LLM, SamplingParams
from vllm.config import CompilationConfig
from dotenv import load_dotenv

load_dotenv()

sampling_params = SamplingParams(temperature=0.8, max_tokens=2000)

compilation_config = CompilationConfig(
    level=2, 
    use_cudagraph=True,
    cudagraph_num_of_warmups=3,
    use_inductor=True, cache_dir='/tmp/vllm_compile_cache'
    )

llm = LLM(model="google/gemma-3-1b-it", compilation_config=compilation_config)

def generate_response(conversation):
    """Generates a response using vLLM."""
    start_time = time.monotonic()

    output = llm.chat(conversation, sampling_params=sampling_params)

    end_time = time.monotonic()
    duration_sec = end_time - start_time

    return output, duration_sec
