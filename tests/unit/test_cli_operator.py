import json
from pathlib import Path

from typer.testing import CliRunner

from liber_harvest.cli import (
    DEFAULT_LM_STUDIO_MODEL,
    DEFAULT_OPENAI_MODEL,
    ProviderMode,
    _provider,
    app,
)
from liber_harvest.providers.lmstudio import LMStudioProvider, ReasoningMode
from liber_harvest.providers.openai import OpenAIProvider, OpenAIReasoning
from liber_harvest.providers.static import StaticProvider

runner = CliRunner()


def test_full_nested_command_tree_builds():
    result = runner.invoke(app, ["harvest", "exegate", "--help"])
    assert result.exit_code == 0, result.output
    assert "--all" in result.output
    assert "--provider" in result.output
    assert "openai" in result.output
    assert "lmstudio" in result.output


def test_providers_command_lists_modes():
    result = runner.invoke(app, ["providers"])
    assert result.exit_code == 0, result.output
    assert "openai" in result.output
    assert "lmstudio" in result.output
    assert "static" in result.output


def test_init_creates_runtime_workspace(tmp_path: Path):
    result = runner.invoke(app, ["init", "--root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "data" / "parsed").is_dir()
    assert (tmp_path / "data" / "bundles").is_dir()
    assert (tmp_path / "harvest").is_dir()


def test_bare_harvest_does_not_assume_lmstudio(tmp_path: Path, monkeypatch):
    source = tmp_path / "song_001.json"
    source.write_text("{}", encoding="utf-8")
    monkeypatch.delenv("LIBER_HARVEST_PROVIDER", raising=False)
    result = runner.invoke(app, ["harvest", "exegate", str(source)])
    assert result.exit_code != 0
    assert "No extraction provider selected" in result.output
    assert "--provider openai" in result.output
    assert "--provider lmstudio" in result.output


def test_provider_uses_openai_defaults(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    monkeypatch.delenv("LIBER_HARVEST_MODEL", raising=False)
    mode, provider = _provider(
        provider=ProviderMode.OPENAI,
        model=None,
        lm_studio_url=None,
        openai_base_url=None,
        response_file=None,
        temperature=0.1,
        max_output_tokens=32768,
        context_length=65536,
        reasoning=ReasoningMode.OFF,
        openai_reasoning=OpenAIReasoning.LOW,
        timeout=600.0,
    )
    assert mode == ProviderMode.OPENAI
    assert isinstance(provider, OpenAIProvider)
    assert provider.model == DEFAULT_OPENAI_MODEL
    assert provider.reasoning == OpenAIReasoning.LOW


def test_provider_uses_lmstudio_defaults(monkeypatch):
    monkeypatch.delenv("LIBER_HARVEST_MODEL", raising=False)
    mode, provider = _provider(
        provider=ProviderMode.LMSTUDIO,
        model=None,
        lm_studio_url=None,
        openai_base_url=None,
        response_file=None,
        temperature=0.1,
        max_output_tokens=32768,
        context_length=65536,
        reasoning=ReasoningMode.OFF,
        openai_reasoning=OpenAIReasoning.LOW,
        timeout=600.0,
    )
    assert mode == ProviderMode.LMSTUDIO
    assert isinstance(provider, LMStudioProvider)
    assert provider.model == DEFAULT_LM_STUDIO_MODEL


def test_response_file_implies_static(tmp_path: Path):
    response = tmp_path / "result.json"
    response.write_text(json.dumps({"contract_version": "x"}), encoding="utf-8")
    mode, provider = _provider(
        provider=None,
        model=None,
        lm_studio_url=None,
        openai_base_url=None,
        response_file=response,
        temperature=0.1,
        max_output_tokens=32768,
        context_length=65536,
        reasoning=ReasoningMode.OFF,
        openai_reasoning=OpenAIReasoning.LOW,
        timeout=600.0,
    )
    assert mode == ProviderMode.STATIC
    assert isinstance(provider, StaticProvider)


def test_openai_requires_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = runner.invoke(
        app,
        ["harvest", "exegate", "missing.json", "--provider", "openai"],
    )
    assert result.exit_code != 0
    assert "OPENAI_API_KEY" in result.output


def test_doctor_without_provider_does_not_contact_lmstudio(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "parsed").mkdir(parents=True)
    (tmp_path / "data" / "bundles").mkdir(parents=True)
    monkeypatch.delenv("LIBER_HARVEST_PROVIDER", raising=False)

    def should_not_run(*args, **kwargs):
        raise AssertionError("LM Studio must not be contacted without provider selection")

    monkeypatch.setattr(LMStudioProvider, "model_status", should_not_run)
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0, result.output
    assert "no extraction provider selected" in result.output
    assert "Doctor passed" in result.output
