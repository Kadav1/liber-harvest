"""LM Studio native v1 chat provider."""
from __future__ import annotations

import json
import time
from typing import Any, Literal

import httpx

from ..adapters.exegate.contract import EXEGATE_HARVEST_SYSTEM_PROMPT
from ..jsonutil import ModelResponseError, parse_json_object
from ..models import HarvestInputEnvelope

ReasoningMode = Literal["off", "low", "medium", "high", "on"]


def normalize_lmstudio_base(url: str) -> str:
    base = url.rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    return base.rstrip("/")


class LMStudioProvider:
    """Call LM Studio's native ``/api/v1/chat`` endpoint.

    Liber Harvest owns the system prompt. The LM Studio UI should not inject a
    second Harvest-specific system prompt. ``context_length`` and ``reasoning``
    are sent per request so a run is not silently governed by unrelated UI
    defaults.
    """

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        temperature: float = 0.1,
        max_output_tokens: int = 32768,
        context_length: int = 65536,
        reasoning: ReasoningMode = "off",
        timeout: float = 600.0,
        http_retries: int = 2,
        api_token: str | None = None,
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

    def _headers(self) -> dict[str, str]:
        if not self.api_token:
            return {}
        return {"Authorization": f"Bearer {self.api_token}"}

    def list_models(self) -> dict[str, Any]:
        with httpx.Client(timeout=min(self.timeout, 30.0)) as client:
            response = client.get(f"{self.base_url}/api/v1/models", headers=self._headers())
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict) or not isinstance(body.get("models"), list):
            raise ValueError("LM Studio /api/v1/models returned an unexpected response")
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

    def _request(self, *, input_text: str, system_prompt: str) -> str:
        payload = {
            "model": self.model,
            "input": input_text,
            "system_prompt": system_prompt,
            "temperature": self.temperature,
            "max_output_tokens": self.max_output_tokens,
            "context_length": self.context_length,
            "reasoning": self.reasoning,
            "store": False,
        }
        last_exc: Exception | None = None
        for attempt in range(self.http_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        f"{self.base_url}/api/v1/chat", json=payload, headers=self._headers()
                    )
                if (response.status_code == 429 or response.status_code >= 500) and attempt < self.http_retries:
                    time.sleep(min(2**attempt, 4))
                    continue
                response.raise_for_status()
                body = response.json()
                for item in body.get("output", []):
                    if item.get("type") != "message":
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
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_exc = exc
                if attempt >= self.http_retries:
                    raise
                time.sleep(min(2**attempt, 4))
        raise RuntimeError("LM Studio request failed") from last_exc

    def extract(self, envelope: HarvestInputEnvelope) -> dict[str, Any]:
        text = self._request(
            input_text=json.dumps(envelope.model_dump(mode="json"), ensure_ascii=False),
            system_prompt=EXEGATE_HARVEST_SYSTEM_PROMPT,
        )
        try:
            return parse_json_object(text)
        except ModelResponseError:
            repaired = self._request(
                input_text=json.dumps(
                    {"source_envelope": envelope.model_dump(mode="json"), "invalid_response": text},
                    ensure_ascii=False,
                ),
                system_prompt=EXEGATE_HARVEST_SYSTEM_PROMPT
                + "\n\nJSON SYNTAX REPAIR\nReturn one syntactically valid JSON object only.",
            )
            return parse_json_object(repaired)

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
                    "invalid_candidate": candidate,
                    "validation_errors": validation_errors,
                },
                ensure_ascii=False,
            ),
            system_prompt=EXEGATE_HARVEST_SYSTEM_PROMPT
            + "\n\nREPAIR MODE\nCorrect the full JSON object without adding new lore.",
        )
        return parse_json_object(text)
