import httpx
import pytest

from liber_harvest.providers.openai import OpenAIProvider, OpenAIReasoning, normalize_openai_base


def test_openai_base_normalization():
    assert normalize_openai_base("https://api.openai.com") == "https://api.openai.com/v1"
    assert normalize_openai_base("https://api.openai.com/v1/") == "https://api.openai.com/v1"


def test_openai_output_text_convenience():
    body = {"output_text": '{"ok":true}'}
    assert OpenAIProvider._extract_output_text(body) == '{"ok":true}'


def test_openai_output_text_from_message_items():
    body = {
        "output": [
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": '{"ok":'},
                    {"type": "output_text", "text": "true}"},
                ],
            }
        ]
    }
    assert OpenAIProvider._extract_output_text(body) == '{"ok":true}'


def test_openai_payload_uses_responses_api(monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200
        def raise_for_status(self):
            return None
        def json(self):
            return {"output_text": '{"ok":true}'}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def post(self, url, json, headers):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return FakeResponse()

    monkeypatch.setattr(httpx, "Client", FakeClient)
    provider = OpenAIProvider(api_key="secret", model="gpt-5.6", reasoning=OpenAIReasoning.LOW)
    text = provider._request(input_text="{}", system_prompt="system")
    assert text == '{"ok":true}'
    assert captured["url"] == "https://api.openai.com/v1/responses"
    assert captured["json"]["model"] == "gpt-5.6"
    assert captured["json"]["instructions"] == "system"
    assert captured["json"]["reasoning"] == {"effort": "low"}
    assert captured["json"]["store"] is False
    assert captured["headers"]["Authorization"] == "Bearer secret"


def test_openai_key_must_not_be_empty():
    with pytest.raises(ValueError):
        OpenAIProvider(api_key="")
