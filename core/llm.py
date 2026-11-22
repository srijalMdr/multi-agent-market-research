"""Thin wrapper around any OpenAI-compatible chat API (Groq, OpenAI, Gemini, ...)."""
from __future__ import annotations

import json
import os
import re
from typing import TypeVar

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, ValidationError

load_dotenv()

T = TypeVar("T", bound=BaseModel)

DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_MODEL = "openai/gpt-oss-120b"


class LLMError(RuntimeError):
    pass


def llm_config() -> dict:
    return {
        "api_key": os.getenv("LLM_API_KEY", "").strip(),
        "base_url": os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL).strip(),
        "model": os.getenv("LLM_MODEL", DEFAULT_MODEL).strip(),
    }


def has_llm_key() -> bool:
    key = llm_config()["api_key"]
    return bool(key) and not key.startswith("your_")


def _client() -> OpenAI:
    cfg = llm_config()
    if not has_llm_key():
        raise LLMError("LLM_API_KEY is missing. Copy .env.example to .env and add your key.")
    return OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"], max_retries=6)


def chat(system: str, user: str, temperature: float = 0.2, json_mode: bool = False) -> str:
    kwargs = {}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    if "gpt-oss" in llm_config()["model"]:
        kwargs["reasoning_effort"] = "low"
    try:
        resp = _client().chat.completions.create(
            model=llm_config()["model"],
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=temperature,
            **kwargs,
        )
    except LLMError:
        raise
    except Exception as e:
        raise LLMError(f"LLM request failed: {e}") from e
    return resp.choices[0].message.content or ""


def _extract_json(text: str) -> dict:
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fenced:
        text = fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in model output")
    return json.loads(text[start : end + 1])


def chat_json(system: str, user: str, model_cls: type[T], retries: int = 1) -> T:
    """Ask for JSON matching `model_cls`, validate with Pydantic, retry once on failure."""
    schema = json.dumps(model_cls.model_json_schema(), indent=None)
    sys_prompt = f"{system}\n\nRespond ONLY with a JSON object matching this JSON schema:\n{schema}"
    prompt = user
    last_err: Exception | None = None
    for _ in range(retries + 1):
        raw = chat(sys_prompt, prompt, json_mode=True)
        try:
            return model_cls.model_validate(_extract_json(raw))
        except (ValueError, ValidationError) as e:
            last_err = e
            prompt = f"{user}\n\nYour previous reply was invalid: {e}\nReturn corrected JSON only."
    raise LLMError(f"Model did not return valid JSON for {model_cls.__name__}: {last_err}")
