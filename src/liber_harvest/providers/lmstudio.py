"""LM Studio provider for local semantic extraction."""

from __future__ import annotations

import json
import time
from enum import StrEnum
from typing import Any

import httpx

from ..adapters.exegate.contract import EXEGATE_HARVEST_SYSTEM_PROMPT
from ..jsonutil import parse_json_object
from ..models import ExegateHarvestResult, HarvestInputEnvelope


class ReasoningMode(StrEnum):
    """LM Studio reasoning modes exposed safely through Typer/Click."""

    OFF = "off"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ON = "on"


class LMStudioHTTPError(ValueError):
    """HTTP failure that preserves LM Studio's server-side diagnostic body."""

    def __init__(self, status_code: int, url: str, body: str):
        self.status_code = status_code
        self.url = url
        self.body = body
        rendered = body.strip() or "<empty response body>"
        if len(rendered) > 4000:
            rendered = rendered[:4000] + "... <truncated>"
        super().__init__(f"LM Studio HTTP {status_code} for {url}: {rendered}")


def normalize_lmstudio_base(url: str) -> str:
    return url.rstrip("/").removesuffix("/v1").rstrip("/")


class LMStudioProvider:
    """Call LM Studio locally without delegating deterministic Harvest duties.

    Native ``/api/v1/chat`` remains the default because it permits an explicit
    per-request context length. Optional structured output uses the official
    OpenAI-compatible ``/v1/chat/completions`` endpoint; for reproducible
    benchmarking that path requires an already-loaded instance at the requested
    context length.
    """

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        temperature: float = 0.1,
        max_output_tokens: int = 8192,
        context_length: int = 65536,
        reasoning: ReasoningMode = ReasoningMode.OFF,
        timeout: float = 600.0,
        http_retries: int = 2,
        api_token: str | None = None,
        structured_output: bool = False,
    ):
        self.base_url = normalize_lmstudio_base(base_url)
        self.model = model
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.context_length = context_length
        self.reasoning = reasoning
        self.timeout = timeout
        self.http_retries = max(0, http_retries)
        self.api_token = api_token
        self.structured_output = structured_output
        self._structured_model_instance_id: str | None = None

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.status_code >= 400:
            raise LMStudioHTTPError(
                response.status_code,
                str(response.request.url),
                response.text,
            )

    def list_models(self) -> dict[str, Any]:
        with httpx.Client(timeout=min(self.timeout, 30.0)) as client:
            response = client.get(
                f"{self.base_url}/api/v1/models", headers=self._headers()
            )
        self._raise_for_status(response)
        body = response.json()
        if not isinstance(body, dict) or not isinstance(body.get("models"), list):
            raise TypeError("LM Studio /api/v1/models returned an unexpected response")
        return body

    def model_status(self) -> dict[str, Any] | None:
        """Return the requested model's model-list record, if installed."""
        for item in self.list_models().get("models", []):
            if not isinstance(item, dict):
                continue
            keys = {str(item.get("key") or ""), str(item.get("display_name") or "")}
            for instance in item.get("loaded_instances") or []:
                if isinstance(instance, dict):
                    keys.add(str(instance.get("id") or ""))
            if self.model in keys:
                return item
        return None

    @staticmethod
    def _instance_context(instance: dict[str, Any]) -> int | None:
        config = instance.get("config") or instance.get("load_config") or {}
        if not isinstance(config, dict):
            return None
        value = config.get("context_length")
        return int(value) if isinstance(value, int) else None

    def benchmark_preflight(self) -> dict[str, Any]:
        if self.max_output_tokens >= self.context_length:
            raise ValueError(
                "LM Studio max_output_tokens must be smaller than context_length "
                f"({self.max_output_tokens} >= {self.context_length})"
            )
        status = self.model_status()
        if status is None:
            raise ValueError(f"LM Studio model {self.model!r} is not installed/visible")

        loaded_contexts: list[int] = []
        matching_instance_id: str | None = None
        for instance in status.get("loaded_instances") or []:
            if not isinstance(instance, dict):
                continue
            context = self._instance_context(instance)
            if context is not None:
                loaded_contexts.append(context)
            instance_id = instance.get("id")
            if (
                self.structured_output
                and context == self.context_length
                and isinstance(instance_id, str)
                and instance_id
                and matching_instance_id is None
            ):
                matching_instance_id = instance_id

        if self.structured_output:
            if matching_instance_id is None:
                raise ValueError(
                    "LM Studio structured-output benchmarking uses /v1/chat/completions, "
                    "which cannot set context_length per request. Pre-load one model instance at "
                    f"context_length={self.context_length}; loaded contexts: "
                    f"{loaded_contexts or 'none'}"
                )
            self._structured_model_instance_id = matching_instance_id
        else:
            self._structured_model_instance_id = None

        return {
            "model": self.model,
            "structured_output": self.structured_output,
            "context_length": self.context_length,
            "loaded_contexts": loaded_contexts,
            "structured_model_instance_id": self._structured_model_instance_id,
        }

    def _post_with_retries(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        last_exc: Exception | None = None
        for attempt in range(self.http_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(url, json=payload, headers=self._headers())
                if (
                    response.status_code == 429 or response.status_code >= 500
                ) and attempt < self.http_retries:
                    time.sleep(min(2**attempt, 4))
                    continue
                self._raise_for_status(response)
                body = response.json()
                if not isinstance(body, dict):
                    raise TypeError("LM Studio returned an unexpected non-object response")
                return body
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_exc = exc
                if attempt >= self.http_retries:
                    raise
                time.sleep(min(2**attempt, 4))
        raise RuntimeError("LM Studio request failed") from last_exc

    def _request_native(self, *, input_text: str, system_prompt: str) -> str:
        payload = {
            "model": self.model,
            "input": input_text,
            "system_prompt": system_prompt,
            "temperature": self.temperature,
            "max_output_tokens": self.max_output_tokens,
            "context_length": self.context_length,
            "reasoning": str(self.reasoning),
            "store": False,
        }
        body = self._post_with_retries(f"{self.base_url}/api/v1/chat", payload)
        for item in body.get("output", []):
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            content = item.get("content", "")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts = []
                for part in content:
                    if isinstance(part, dict):
                        value = part.get("text") or part.get("content")
                        if value:
                            parts.append(str(value))
                if parts:
                    return "".join(parts)
        raise ValueError("LM Studio response did not contain a message output")

    def _request_structured(self, *, input_text: str, system_prompt: str) -> str:
        if self._structured_model_instance_id is None:
            raise ValueError(
                "Structured LM Studio requests require benchmark_preflight() to bind an exact "
                "loaded model instance"
            )
        schema = ExegateHarvestResult.model_json_schema()
        payload = {
            "model": self._structured_model_instance_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": input_text},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "exegate_harvest_result",
                    "strict": True,
                    "schema": schema,
                },
            },
            "temperature": self.temperature,
            "max_tokens": self.max_output_tokens,
            "stream": False,
        }
        body = self._post_with_retries(
            f"{self.base_url}/v1/chat/completions", payload
        )
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ValueError("LM Studio structured response did not contain choices")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise ValueError("LM Studio structured response did not contain message content")
        return content

    def _request(self, *, input_text: str, system_prompt: str) -> str:
        if self.structured_output:
            return self._request_structured(
                input_text=input_text, system_prompt=system_prompt
            )
        return self._request_native(input_text=input_text, system_prompt=system_prompt)

    def extract(self, envelope: HarvestInputEnvelope) -> dict[str, Any]:
        text = self._request(
            input_text=json.dumps(envelope.model_dump(mode="json"), ensure_ascii=False),
            system_prompt=EXEGATE_HARVEST_SYSTEM_PROMPT,
        )
        return parse_json_object(text)

    def repair(
        self,
        candidate: dict[str, Any],
        validation_errors: str,
        envelope: HarvestInputEnvelope,
    ) -> dict[str, Any]:
        text = self._request(
            input_text=json.dumps(
                {
                    "source_envelope": envelope.model_dump(mode="json"),
                    "invalid_fragment_subset": candidate,
                    "validation_errors": validation_errors,
                },
                ensure_ascii=False,
            ),
            system_prompt=EXEGATE_HARVEST_SYSTEM_PROMPT
            + "\n\nFRAGMENT-SCOPED REPAIR MODE\n"
            + "Correct only the supplied invalid fragment subset. Return one full "
            + "ExegateHarvestResult object containing exactly those repaired fragments. "
            + "Do not add unrelated lore.",
        )
        return parse_json_object(text)
