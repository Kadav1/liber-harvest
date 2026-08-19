"""Hosted OpenAI Responses API provider."""
from __future__ import annotations

import json
import time
from enum import StrEnum
from typing import Any

import httpx

from ..adapters.exegate.contract import EXEGATE_HARVEST_SYSTEM_PROMPT
from ..jsonutil import parse_json_object
from ..models import HarvestInputEnvelope


class OpenAIReasoning(StrEnum):
    NONE = "none"
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"


def normalize_openai_base(url: str) -> str:
    base = url.rstrip("/")
    if not base.endswith("/v1"):
        base += "/v1"
    return base


class OpenAIProvider:
    """Use OpenAI's hosted Responses API as the semantic extraction backend.

    The provider only produces draft extraction JSON. Stable IDs, provenance
    spans, hashes, materialization and output manifests remain deterministic
    responsibilities of Liber Harvest.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-5.6",
        base_url: str = "https://api.openai.com/v1",
        reasoning: OpenAIReasoning = OpenAIReasoning.LOW,
        max_output_tokens: int = 32768,
        timeout: float = 600.0,
        http_retries: int = 2,
    ):
        if not api_key.strip():
            raise ValueError("OpenAI API key must not be empty")
        self.api_key = api_key
        self.model = model
        self.base_url = normalize_openai_base(base_url)
        self.reasoning = reasoning
        self.max_output_tokens = max_output_tokens
        self.timeout = timeout
        self.http_retries = max(0, http_retries)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _extract_output_text(body: dict[str, Any]) -> str:
        convenience = body.get("output_text")
        if isinstance(convenience, str) and convenience.strip():
            return convenience

        parts: list[str] = []
        for item in body.get("output") or []:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            for content in item.get("content") or []:
                if not isinstance(content, dict):
                    continue
                if content.get("type") == "output_text" and content.get("text"):
                    parts.append(str(content["text"]))
        if parts:
            return "".join(parts)
        raise ValueError("OpenAI response did not contain output text")

    def model_status(self) -> dict[str, Any] | None:
        with httpx.Client(timeout=min(self.timeout, 30.0)) as client:
            response = client.get(f"{self.base_url}/models/{self.model}", headers=self._headers())
        if response.status_code == 404:
            return None
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict):
            raise TypeError("OpenAI model lookup returned an unexpected response")
        return body

    def _request(self, *, input_text: str, system_prompt: str) -> str:
        payload = {
            "model": self.model,
            "instructions": system_prompt,
            "input": input_text,
            "reasoning": {"effort": str(self.reasoning)},
            "max_output_tokens": self.max_output_tokens,
            "store": False,
        }
        last_exc: Exception | None = None
        for attempt in range(self.http_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        f"{self.base_url}/responses", json=payload, headers=self._headers()
                    )
                if (response.status_code == 429 or response.status_code >= 500) and attempt < self.http_retries:
                    time.sleep(min(2**attempt, 4))
                    continue
                response.raise_for_status()
                body = response.json()
                if not isinstance(body, dict):
                    raise TypeError("OpenAI Responses API returned an unexpected response")
                return self._extract_output_text(body)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_exc = exc
                if attempt >= self.http_retries:
                    raise
                time.sleep(min(2**attempt, 4))
        raise RuntimeError("OpenAI request failed") from last_exc

    def extract(self, envelope: HarvestInputEnvelope) -> dict[str, Any]:
        # v0.1.7 removes the provider-internal syntax-repair call so a case has
        # one extraction plus at most one pipeline-owned fragment repair.
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
