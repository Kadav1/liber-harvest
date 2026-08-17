from pathlib import Path

from typer.testing import CliRunner

from liber_harvest.cli import DEFAULT_MODEL, _provider, app
from liber_harvest.providers.lmstudio import LMStudioProvider

runner = CliRunner()


def test_init_creates_runtime_workspace(tmp_path: Path):
    result = runner.invoke(app, ["init", "--root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "data" / "parsed").is_dir()
    assert (tmp_path / "data" / "bundles").is_dir()
    assert (tmp_path / "harvest").is_dir()
    assert "runtime workspace ready" in result.output


def test_provider_uses_operator_defaults(monkeypatch):
    monkeypatch.delenv("LIBER_HARVEST_MODEL", raising=False)
    provider = _provider(
        model=None,
        lm_studio_url=None,
        response_file=None,
        temperature=0.1,
        max_output_tokens=32768,
        context_length=65536,
        reasoning="off",
        timeout=600.0,
    )
    assert isinstance(provider, LMStudioProvider)
    assert provider.model == DEFAULT_MODEL
    assert provider.base_url == "http://127.0.0.1:1234"
    assert provider.context_length == 65536
    assert provider.reasoning == "off"


def test_lmstudio_token_header():
    provider = LMStudioProvider(base_url="http://127.0.0.1:1234", model="example", api_token="secret")
    assert provider._headers() == {"Authorization": "Bearer secret"}


def test_doctor_passes_with_loaded_compatible_model(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "parsed").mkdir(parents=True)
    (tmp_path / "data" / "bundles").mkdir(parents=True)

    def fake_status(self):
        return {
            "type": "llm",
            "key": DEFAULT_MODEL,
            "loaded_instances": [{"id": DEFAULT_MODEL, "config": {"context_length": 65536}}],
            "max_context_length": 262144,
            "capabilities": {"reasoning": {"allowed_options": ["off", "on"], "default": "on"}},
        }

    monkeypatch.setattr(LMStudioProvider, "model_status", fake_status)
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0, result.output
    assert "Doctor passed" in result.output
    assert "model is loaded" in result.output
    assert "reasoning mode supported: off" in result.output
