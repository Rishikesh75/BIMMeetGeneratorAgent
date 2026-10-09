"""Load the published SmolLM2 LoRA and turn text into hierarchical BIM JSON."""

from __future__ import annotations

import json
import logging
import os
import re
import threading
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_BASE_MODEL = "HuggingFaceTB/SmolLM2-360M-Instruct"
DEFAULT_ADAPTER_ID = "Rishi74518/smollm2-360m-bim-lora"
DEFAULT_MAX_NEW_TOKENS = 768

SYSTEM_PROMPT = (
    "You convert natural-language BIM requests into one JSON object and nothing else. "
    "No Markdown, no explanation, and no text after the closing brace. "
    "The top-level keys must be exactly project, site, building, storeys, elements, "
    "materials, relationships, metadata, in that order. "
    "Do not add extra keys. Stop when the object is closed. "
    "Preserve IDs, references, meters, and the right_handed_z_up coordinate system."
)

EXPECTED_KEYS = {
    "project",
    "site",
    "building",
    "storeys",
    "elements",
    "materials",
    "relationships",
    "metadata",
}


class ModelNotReadyError(RuntimeError):
    """Raised when generation is requested before the adapter has loaded."""


@dataclass
class GenerationResult:
    raw_text: str
    valid_json: bool
    valid_structure: bool
    plan: dict[str, Any] | None


def parse_model_output(raw_text: str) -> GenerationResult:
    """Parse a model completion into hierarchical JSON and structure flags."""
    parsed = _loads_json_value(raw_text)
    if not isinstance(parsed, dict):
        return GenerationResult(
            raw_text=raw_text,
            valid_json=parsed is not None,
            valid_structure=False,
            plan=None,
        )
    return GenerationResult(
        raw_text=raw_text,
        valid_json=True,
        valid_structure=set(parsed) == EXPECTED_KEYS,
        plan=parsed,
    )


def invalid_json_detail(result: GenerationResult) -> dict[str, Any]:
    return {
        "message": "Model response was not valid JSON",
        "raw_text": result.raw_text,
        "valid_json": False,
        "valid_structure": False,
    }


def unusable_plan_detail(result: GenerationResult) -> dict[str, Any] | None:
    """Detail payload for a 422 when the completion is not a JSON object.

    MVP: this rejection is commented out so /plan/generate returns the model
    text even when it is not valid JSON. Restore the block below later.
    """
    return None
    # if result.plan is not None:
    #     return None
    # if not result.valid_json:
    #     return invalid_json_detail(result)
    # return {
    #     "message": "Model response was not a JSON object",
    #     "raw_text": result.raw_text,
    #     "valid_json": True,
    #     "valid_structure": False,
    # }


class BimLlmService:
    """One CPU-resident LoRA model, loaded once and shared by every request."""

    def __init__(self) -> None:
        self._model: Any = None
        self._tokenizer: Any = None
        self._lock = threading.Lock()
        self._loaded = False
        self._load_error: str | None = None

    @property
    def loaded(self) -> bool:
        return self._loaded

    @property
    def load_error(self) -> str | None:
        return self._load_error

    @property
    def base_model(self) -> str:
        return os.environ.get("BIM_BASE_MODEL", DEFAULT_BASE_MODEL).strip() or DEFAULT_BASE_MODEL

    @property
    def adapter_id(self) -> str:
        return os.environ.get("BIM_ADAPTER_ID", DEFAULT_ADAPTER_ID).strip() or DEFAULT_ADAPTER_ID

    @property
    def adapter_path(self) -> str | None:
        path = os.environ.get("BIM_ADAPTER_PATH", "").strip()
        return path or None

    @property
    def max_new_tokens(self) -> int:
        raw = os.environ.get("BIM_MAX_NEW_TOKENS", str(DEFAULT_MAX_NEW_TOKENS)).strip()
        try:
            value = int(raw)
        except ValueError:
            return DEFAULT_MAX_NEW_TOKENS
        return value if value > 0 else DEFAULT_MAX_NEW_TOKENS

    def status(self) -> dict[str, Any]:
        return {
            "model_loaded": self._loaded,
            "base_model": self.base_model,
            "adapter_id": self.adapter_id,
            "adapter_path": self.adapter_path,
            "error": self._load_error,
        }

    def load(self) -> None:
        """Download the public base model and the published LoRA, then keep them on CPU."""
        if self._loaded:
            return

        adapter_source = self.adapter_path or self.adapter_id
        logger.info(
            "Loading BIM model base=%s adapter=%s",
            self.base_model,
            adapter_source,
        )
        try:
            import torch
            from peft import PeftModel
            from transformers import AutoModelForCausalLM, AutoTokenizer

            tokenizer = AutoTokenizer.from_pretrained(adapter_source)
            if tokenizer.pad_token_id is None:
                tokenizer.pad_token = tokenizer.eos_token

            base_model = AutoModelForCausalLM.from_pretrained(
                self.base_model,
                dtype=torch.float32,
                low_cpu_mem_usage=True,
            )
            model = PeftModel.from_pretrained(base_model, adapter_source)
            model.eval()
        except Exception as exc:
            self._loaded = False
            self._model = None
            self._tokenizer = None
            self._load_error = str(exc)
            logger.exception("BIM model failed to load")
            raise

        self._tokenizer = tokenizer
        self._model = model
        self._loaded = True
        self._load_error = None
        logger.info("BIM model loaded on CPU")

    def generate(self, description: str) -> GenerationResult:
        if not self._loaded or self._model is None or self._tokenizer is None:
            raise ModelNotReadyError(self._load_error or "BIM model is not loaded")

        prompt = description.strip()
        with self._lock:
            raw_text = self._generate_locked(prompt)
        return parse_model_output(raw_text)

    def _generate_locked(self, prompt: str) -> str:
        import torch

        tokenizer = self._tokenizer
        model = self._model
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = tokenizer(text, return_tensors="pt")
        with torch.inference_mode():
            output = model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        generated_ids = output[0, inputs["input_ids"].shape[1] :]
        return tokenizer.decode(generated_ids, skip_special_tokens=True).strip()


def _loads_json_value(raw_text: str) -> Any | None:
    candidate = raw_text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate, flags=re.IGNORECASE)
        candidate = re.sub(r"\s*```$", "", candidate)

    parsed = _json_loads(candidate)
    if parsed is not None:
        return parsed

    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end <= start:
        return None
    return _json_loads(candidate[start : end + 1])


def _json_loads(text: str) -> Any | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


bim_llm = BimLlmService()
