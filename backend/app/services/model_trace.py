"""Task-local model provider trace populated by the LLM adapter."""

from contextvars import ContextVar
import hashlib


_model_trace: ContextVar[dict | None] = ContextVar("nexora_model_trace", default=None)


def start_model_trace():
    return _model_trace.set({"provider": None, "model": None, "prompt_hash": None})


def record_model_call(provider: str, model: str):
    trace = _model_trace.get()
    if trace is not None:
        trace["provider"] = provider
        trace["model"] = model


def record_prompt(system_prompt: str):
    trace = _model_trace.get()
    if trace is not None:
        trace["prompt_hash"] = hashlib.sha256(
            system_prompt.encode("utf-8")
        ).hexdigest()


def get_model_trace() -> dict:
    return dict(_model_trace.get() or {})


def reset_model_trace(token):
    _model_trace.reset(token)
