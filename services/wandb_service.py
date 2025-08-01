import logging
import atexit
import wandb
from vllm import RequestOutput

logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

_wandb_initialized = False
_run = None


def init_wandb(
    project_name: str = "mm-chat-comparison",
    run_name: str = None,
    config: dict = None,
    job_type: str = "chat_application",
):
    """
    Initializes a new W&B run.
    Ensure WANDB_API_KEY environment variable is set.
    """
    global _wandb_initialized, _run
    if _wandb_initialized:
        logger.info("W&B is already initialized.")
        return

    try:
        _run = wandb.init(
            project=project_name,
            name=run_name,
            config=config,
            job_type=job_type,
            reinit=True,
        )
        _wandb_initialized = True
        logger.info(
            f"W&B initialized for project '{project_name}', run_id: {_run.id if _run else 'N/A'}"
        )
        # Register finish_wandb_run to be called on normal program termination
        atexit.register(finish_wandb_run)
    except Exception as e:
        logger.error(f"Failed to initialize W&B: {e}")
        _wandb_initialized = False
        _run = None


def log_metrics(metrics: dict, step: int = None):
    """
    Logs a dictionary of metrics to W&B.
    """
    if _wandb_initialized and _run:
        try:
            _run.log(metrics, step=step)
            logger.debug(f"Logged metrics to W&B: {metrics}")
        except Exception as e:
            logger.error(f"Failed to log metrics to W&B: {e}")
    elif not _wandb_initialized:
        logger.debug("W&B not initialized. Skipping metrics logging.")
        pass


def log_generation_data(
    input_tok_s: float = None,
    output_tok_s: float = None,
    latency_ms: float = None,
    **kwargs,
):
    """
    Logs token generation speed, latency, and any additional key-value pairs.
    """
    metrics_to_log = {}
    if input_tok_s is not None:
        metrics_to_log["input_tok_per_sec"] = input_tok_s
    if output_tok_s is not None:
        metrics_to_log["output_tok_per_sec"] = output_tok_s
    if latency_ms is not None:
        metrics_to_log["generation_latency_ms"] = latency_ms

    metrics_to_log.update(kwargs)  # Add any other metrics passed

    if metrics_to_log:
        log_metrics(metrics_to_log)


def finish_wandb_run():
    """
    Finishes the current W&B run, if active.
    Called automatically on exit if init_wandb was successful.
    """
    global _wandb_initialized, _run
    if _wandb_initialized and _run:
        logger.info(f"Attempting to finish W&B run: {_run.id}")
        try:
            wandb.finish()  # wandb.finish() uses the current active run
            logger.info(f"W&B run {_run.id} finished.")
        except Exception as e:
            logger.error(f"Error finishing W&B run {_run.id}: {e}")
        finally:
            _wandb_initialized = False
            _run = None
    elif _run and not _wandb_initialized:  # If run was attempted but failed init
        _run = None


def log_vllm_request_output_metrics(
    vllm_request_output: RequestOutput if RequestOutput else "typing.Any",
    manual_duration_sec: float = None,
):
    """Extracts metrics from vLLM's RequestOutput and logs them to W&B."""
    if not vllm_request_output:
        logger.warning("log_vllm_request_output_metrics called with None input.")
        return

    # Always calculate token counts
    num_prompt_tokens = len(vllm_request_output.prompt_token_ids)
    num_generated_tokens = 0
    if vllm_request_output.outputs and len(vllm_request_output.outputs) > 0:
        num_generated_tokens = len(vllm_request_output.outputs[0].token_ids)
    else:
        logger.warning(
            f"No outputs found in vLLM RequestOutput for request_id: {vllm_request_output.request_id} when calculating token counts."
        )

    # Base metrics that are always available
    metrics_to_log = {
        "request_id": vllm_request_output.request_id,
        "num_prompt_tokens": num_prompt_tokens,
        "num_generated_tokens": num_generated_tokens,
        "finished": vllm_request_output.finished,  # from vLLM RequestOutput
    }

    # Add manual duration and derived metrics if available
    if manual_duration_sec is not None:
        metrics_to_log["manual_total_generation_time_sec"] = manual_duration_sec
        if num_generated_tokens > 0 and manual_duration_sec > 0:
            metrics_to_log["manual_output_tok_per_sec"] = (
                num_generated_tokens / manual_duration_sec
            )
        elif num_generated_tokens > 0 and manual_duration_sec == 0:
            metrics_to_log["manual_output_tok_per_sec"] = float("inf")
        elif num_generated_tokens == 0:
            metrics_to_log["manual_output_tok_per_sec"] = 0.0

    # Process and add detailed metrics from vLLM if they exist
    if vllm_request_output.metrics:
        metrics = vllm_request_output.metrics
        num_prompt_tokens = len(vllm_request_output.prompt_token_ids)

        num_generated_tokens = 0
        if vllm_request_output.outputs and len(vllm_request_output.outputs) > 0:
            num_generated_tokens = len(vllm_request_output.outputs[0].token_ids)
        else:
            logger.warning(
                f"No outputs found in vLLM RequestOutput for request_id: {vllm_request_output.request_id}"
            )

        # Initialize metrics to None
        prompt_processing_time_sec = None
        generation_time_sec = None
        input_tok_per_sec = None
        output_tok_per_sec = None
        total_latency_ms = None
        time_to_first_token_ms = None

        # Calculate metrics based on available timestamps
        if metrics.arrival_time is not None:
            if (
                metrics.first_scheduled_time is not None
                and metrics.first_token_time is not None
            ):
                prompt_processing_time_sec = (
                    metrics.first_token_time - metrics.first_scheduled_time
                )

            if metrics.first_token_time is not None:
                time_to_first_token_ms = (
                    metrics.first_token_time - metrics.arrival_time
                ) * 1000

            if metrics.finished_time is not None:
                total_latency_ms = (metrics.finished_time - metrics.arrival_time) * 1000

        if metrics.first_token_time is not None and metrics.last_token_time is not None:
            generation_time_sec = metrics.last_token_time - metrics.first_token_time

        # Calculate input tokens per second
        if num_prompt_tokens > 0:
            if (
                prompt_processing_time_sec is not None
                and prompt_processing_time_sec > 0
            ):
                input_tok_per_sec = num_prompt_tokens / prompt_processing_time_sec
            elif prompt_processing_time_sec == 0:  # Effectively infinite if tokens > 0
                input_tok_per_sec = float("inf")
        elif num_prompt_tokens == 0:
            input_tok_per_sec = 0.0

        # Calculate output tokens per second
        if num_generated_tokens > 0:
            if generation_time_sec is not None and generation_time_sec > 0:
                output_tok_per_sec = num_generated_tokens / generation_time_sec
            elif generation_time_sec == 0:  # Effectively infinite if tokens > 0
                output_tok_per_sec = float("inf")
        elif num_generated_tokens == 0:  # No generated tokens
            output_tok_per_sec = 0.0

        metrics_to_log = {
            "request_id": vllm_request_output.request_id,
            "num_prompt_tokens": num_prompt_tokens,
            "num_generated_tokens": num_generated_tokens,
            "time_in_queue_sec": metrics.time_in_queue,  # Directly available
            "prompt_processing_time_sec": prompt_processing_time_sec,
            "time_to_first_token_ms": time_to_first_token_ms,
            "generation_time_sec": generation_time_sec,
            "total_latency_ms": total_latency_ms,
            "input_tok_per_sec": input_tok_per_sec,
            "output_tok_per_sec": output_tok_per_sec,
        }

        # Add other simple metrics if they exist and are useful, e.g., scheduler_time
        if hasattr(metrics, "scheduler_time") and isinstance(
            metrics.scheduler_time, (int, float)
        ):
            metrics_to_log["vllm_scheduler_time_sec"] = metrics.scheduler_time

        # Filter out None values before logging
        metrics_to_log_filtered = {
            k: v for k, v in metrics_to_log.items() if v is not None
        }

        if metrics_to_log_filtered:
            log_metrics(metrics_to_log_filtered)
        else:
            logger.info(
                "No valid metrics to log for request_id: %s",
                vllm_request_output.request_id,
            )

    else:
        # This warning now specifically refers to vLLM's internal detailed metrics
        logger.warning(
            "No internal detailed metrics (vllm_request_output.metrics) found in vLLM RequestOutput for request_id: %s. Manual metrics may still be logged.",
            vllm_request_output.request_id,
        )

    # Filter out ALL None values from the combined metrics_to_log before logging
    # This was previously inside the 'if vllm_request_output.metrics:' block
    metrics_to_log_filtered = {k: v for k, v in metrics_to_log.items() if v is not None}

    if metrics_to_log_filtered:
        # Ensure request_id is always present if it somehow became None (it shouldn't from RequestOutput)
        if "request_id" not in metrics_to_log_filtered and hasattr(
            vllm_request_output, "request_id"
        ):
            metrics_to_log_filtered["request_id"] = vllm_request_output.request_id
        log_metrics(metrics_to_log_filtered)
    else:
        # This case should be rare now, as we always have token counts and request_id
        logger.info(
            "No valid metrics to log after filtering for request_id: %s",
            vllm_request_output.request_id,
        )
