import json
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from liber_harvest.benchmark_cli import app as benchmark_app
from liber_harvest.benchmark_runtime import (
    BenchmarkPreflightError,
    compare_summaries,
    run_model_benchmark,
)
from liber_harvest.corrections import (
    all_validation_errors_fragment_local,
    apply_deterministic_corrections,
    fragment_error_indices,
    make_fragment_repair_subset,
    merge_fragment_repair,
)
from liber_harvest.models import ExegateHarvestResult, HarvestInputEnvelope
from liber_harvest.pipeline import HarvestContractError, LiberHarvester
from liber_harvest.providers.lmstudio import LMStudioHTTPError, LMStudioProvider

SHA = "a" * 64
runner = CliRunner()


def _envelope() -> HarvestInputEnvelope:
    return HarvestInputEnvelope(
        source_path="data/parsed/song_006.json",
        source_sha256=SHA,
        source_format="exegate_run_json",
        source={
            "song_title": "Blood-Sweat in the Dust of Judgment",
            "prima_materia_raw": 'The prayer says "Deus, Judica Me" before the dust.',
            "naming_ids_raw": None,
            "scene_hooks": [
                {"hook_text_raw": "A proposed vigil scene."},
            ],
        },
    )


def _base_candidate() -> dict:
    return {
        "contract_version": "exegate-harvest/0.1.2",
        "source": {
            "pipeline": "Infernal Exegate v5.4 UNIFIED",
            "source_path": "wrong.json",
            "source_sha256": "b" * 64,
            "source_title": "wrong",
            "bundle_id": None,
        },
        "fragments": [],
        "coverage": [],
        "discarded": [],
        "warnings": [],
    }


def test_deterministic_correction_repairs_t01_scalar_pointer_and_structure():
    candidate = _base_candidate()
    candidate["fragments"] = [
        {
            "concept_key": "prayer_judgment_verdict",
            "type": "phrase",
            "title": "Deus, Judica Me",
            "claim": {"modality": "asserted"},
            "content": {
                "source_meaning": "A prayer for judgment.",
                "normalized_lore": "A prayer for judgment.",
                "details": {"function": "verdict"},
            },
            "domains": ["language"],
            "tags": ["judgment"],
            "legacy_bindings": [],
            "derivation": {
                "primary_mode": "decomposed",
                "operations": ["direct", "generalized"],
                "fidelity": "high",
            },
            "provenance": [
                {
                    "pipeline": "Infernal Exegate v5.4 UNIFIED",
                    "source_path": "wrong.json",
                    "source_sha256": "b" * 64,
                    "source_title": "wrong",
                    "bundle_id": None,
                    "source_item_id": None,
                    "circle": None,
                    "evidence_layer": "source_semantics",
                    "source_modality": "asserted",
                    "json_pointer": "/prima_materia_raw/1",
                    "role": "primary",
                    "excerpt": '"Deus, Judica Me"',
                }
            ],
            "relation_hints": [],
            "review": {"required": False, "reasons": []},
        }
    ]
    corrected, changes = apply_deterministic_corrections(candidate, _envelope())
    fragment = corrected["fragments"][0]
    anchor = fragment["provenance"][0]
    assert corrected["source"]["pipeline"] == "exegate"
    assert corrected["source"]["source_path"] == "data/parsed/song_006.json"
    assert fragment["content"]["details"] == ["function: verdict"]
    assert fragment["derivation"]["operations"] == ["decomposed", "generalized"]
    assert anchor["json_pointer"] == "/prima_materia_raw"
    assert anchor["circle"] == "prima_materia"
    assert changes


def test_deterministic_correction_removes_null_metadata_fragment():
    candidate = _base_candidate()
    candidate["fragments"] = [
        {
            "concept_key": "naming_ids_null_metadata",
            "type": "other",
            "title": "Naming IDs Null",
            "claim": {"modality": "asserted"},
            "content": {
                "source_meaning": "The field is null.",
                "normalized_lore": "No naming system is present.",
                "details": [],
            },
            "domains": [],
            "tags": ["naming"],
            "legacy_bindings": [],
            "derivation": {
                "primary_mode": "direct",
                "operations": ["direct"],
                "fidelity": "high",
            },
            "provenance": [
                {
                    "pipeline": "exegate",
                    "source_path": "data/parsed/song_006.json",
                    "source_sha256": SHA,
                    "source_title": "Blood-Sweat in the Dust of Judgment",
                    "bundle_id": None,
                    "source_item_id": None,
                    "circle": "naming_ids",
                    "evidence_layer": "metadata",
                    "source_modality": "asserted",
                    "json_pointer": "/naming_ids_raw",
                    "role": "primary",
                    "excerpt": "null",
                }
            ],
            "relation_hints": [],
            "review": {"required": False, "reasons": []},
        }
    ]
    candidate["coverage"] = [
        {
            "json_pointer": "/naming_ids_raw",
            "disposition": "extracted",
            "evidence_layer": "metadata",
            "source_modality": "asserted",
            "concept_keys": ["naming_ids_null_metadata"],
        }
    ]
    corrected, _ = apply_deterministic_corrections(candidate, _envelope())
    assert corrected["fragments"] == []
    assert corrected["coverage"][0]["disposition"] == "empty"
    assert corrected["coverage"][0]["concept_keys"] == []
    assert corrected["discarded"][0]["reason"] == "empty"


def test_t01_regression_fragment_repair_subset_does_not_resend_whole_candidate():
    candidate = _base_candidate()
    huge_unrelated = "x" * 50000
    candidate["fragments"] = [
        {
            "concept_key": "valid_unrelated_fragment",
            "type": "phrase",
            "title": "Unrelated",
            "claim": {"modality": "asserted"},
            "content": {
                "source_meaning": huge_unrelated,
                "normalized_lore": huge_unrelated,
                "details": [],
            },
            "domains": [],
            "tags": [],
            "legacy_bindings": [],
            "derivation": {
                "primary_mode": "direct",
                "operations": ["direct"],
                "fidelity": "high",
            },
            "provenance": [],
            "relation_hints": [],
            "review": {"required": False, "reasons": []},
        },
        {"concept_key": "broken_target_fragment"},
    ]
    with pytest.raises(ValidationError) as caught:
        ExegateHarvestResult.model_validate(candidate)
    indices = fragment_error_indices(caught.value)
    assert 1 in indices
    subset = make_fragment_repair_subset(candidate, (1,))
    assert subset is not None
    assert len(subset["fragments"]) == 1
    assert huge_unrelated not in json.dumps(subset)
    assert len(json.dumps(subset)) < len(json.dumps(candidate)) / 10


def test_fragment_repair_can_fix_concept_key_and_remaps_coverage():
    candidate = _base_candidate()
    candidate["fragments"] = [{"concept_key": "INVALID KEY"}]
    candidate["coverage"] = [
        {
            "json_pointer": "/prima_materia_raw",
            "disposition": "extracted",
            "evidence_layer": "source_semantics",
            "source_modality": "asserted",
            "concept_keys": ["INVALID KEY"],
        }
    ]
    repaired = {
        **_base_candidate(),
        "fragments": [{"concept_key": "valid_key"}],
    }
    merged = merge_fragment_repair(candidate, (0,), repaired)
    assert merged["fragments"][0]["concept_key"] == "valid_key"
    assert merged["coverage"][0]["concept_keys"] == ["valid_key"]


def test_mixed_scope_validation_error_is_not_fragment_repairable():
    candidate = _base_candidate()
    candidate.pop("source")
    candidate["fragments"] = [{"concept_key": "broken_fragment"}]
    with pytest.raises(ValidationError) as caught:
        ExegateHarvestResult.model_validate(candidate)
    assert fragment_error_indices(caught.value) == (0,)
    assert not all_validation_errors_fragment_local(caught.value)


class MixedScopeProvider:
    def __init__(self):
        self.repair_calls = 0

    def extract(self, envelope):
        del envelope
        candidate = _base_candidate()
        candidate.pop("source")
        candidate["fragments"] = [{"concept_key": "broken_fragment"}]
        return candidate

    def repair(self, candidate, validation_errors, envelope):
        del candidate, validation_errors, envelope
        self.repair_calls += 1
        raise AssertionError("mixed-scope validation must not invoke repair")


def test_pipeline_does_not_spend_repair_call_on_mixed_scope_error():
    provider = MixedScopeProvider()
    harvester = LiberHarvester(provider, max_repairs=1)
    with pytest.raises(HarvestContractError, match="non-fragment schema errors"):
        harvester._extract_and_validate(_envelope())
    assert provider.repair_calls == 0


def test_lmstudio_http_error_preserves_server_body():
    request = httpx.Request("POST", "http://host:1234/api/v1/chat")
    response = httpx.Response(
        400,
        request=request,
        text='{"error":{"message":"request (19888 tokens) exceeds context 16384"}}',
    )
    with pytest.raises(LMStudioHTTPError) as caught:
        LMStudioProvider._raise_for_status(response)
    assert "19888 tokens" in str(caught.value)
    assert "16384" in str(caught.value)


def test_lmstudio_structured_preflight_binds_exact_loaded_instance(monkeypatch):
    provider = LMStudioProvider(
        base_url="http://host:1234",
        model="qwen/qwen3.5-9b",
        context_length=16384,
        max_output_tokens=4096,
        structured_output=True,
    )
    monkeypatch.setattr(
        provider,
        "list_models",
        lambda: {
            "models": [
                {
                    "key": "qwen/qwen3.5-9b",
                    "display_name": "Qwen3.5 9B",
                    "loaded_instances": [
                        {"id": "wrong-context", "config": {"context_length": 8192}},
                        {"id": "harvest-qwen-16k", "config": {"context_length": 16384}},
                    ],
                }
            ]
        },
    )
    meta = provider.benchmark_preflight()
    assert meta["structured_model_instance_id"] == "harvest-qwen-16k"

    captured = {}

    def fake_post(url, payload):
        captured["url"] = url
        captured["payload"] = payload
        return {"choices": [{"message": {"content": "{}"}}]}

    monkeypatch.setattr(provider, "_post_with_retries", fake_post)
    assert provider._request_structured(input_text="x", system_prompt="y") == "{}"
    assert captured["url"].endswith("/v1/chat/completions")
    assert captured["payload"]["model"] == "harvest-qwen-16k"
    response_format = captured["payload"]["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["schema"]["type"] == "object"


def test_benchmark_cli_rejects_impossible_context_budget_before_network():
    result = runner.invoke(
        benchmark_app,
        [
            "run",
            "--provider",
            "lmstudio",
            "--model",
            "qwen/qwen3.5-9b",
            "--context-length",
            "16384",
            "--max-output-tokens",
            "32768",
        ],
    )
    assert result.exit_code != 0
    assert "must be smaller than --context-length" in result.output


class NeverExtractProvider:
    def __init__(self):
        self.extract_calls = 0

    def benchmark_preflight(self):
        return {"ok": True}

    def extract(self, envelope):
        del envelope
        self.extract_calls += 1
        raise AssertionError("preflight must abort before inference")

    def repair(self, candidate, validation_errors, envelope):
        del candidate, validation_errors, envelope
        raise AssertionError("repair must not run")


def test_suite_preflight_aborts_before_inference_when_source_missing(tmp_path: Path):
    calibration = tmp_path / "calibration" / "T01"
    calibration.mkdir(parents=True)
    (calibration / "case.json").write_text(
        json.dumps(
            {
                "case_id": "T01",
                "historical_source_key": "song_006",
                "purpose": "test",
                "targets": [],
                "status": "frozen-regression",
                "source_distribution": "external-legacy-corpus",
                "contract_version": "exegate-harvest/0.1.2",
            }
        ),
        encoding="utf-8",
    )
    provider = NeverExtractProvider()
    with pytest.raises(BenchmarkPreflightError) as caught:
        run_model_benchmark(
            provider=provider,
            provider_name="lmstudio",
            model_label="test",
            corpus_root=tmp_path / "data",
            calibration_root=tmp_path / "calibration",
            out_root=tmp_path / "out",
        )
    assert "T01" in str(caught.value)
    assert provider.extract_calls == 0
    assert not (tmp_path / "out").exists()


def test_compare_puts_unrankable_run_after_eligible_run(tmp_path: Path):
    eligible = tmp_path / "eligible.json"
    broken = tmp_path / "broken.json"
    base = {
        "benchmark_version": "model-selection/0.1",
        "provider": "lmstudio",
        "cases_requested": 11,
        "cases_completed": 11,
        "cases_failed": 0,
        "mean_compliance_score": 80.0,
        "target_pass_pct": 80.0,
        "total_repair_calls": 0,
        "total_semantic_seconds": 1.0,
    }
    eligible.write_text(
        json.dumps(
            {
                **base,
                "model": "eligible",
                "ranking_eligible": True,
                "selection_score": 80.0,
            }
        ),
        encoding="utf-8",
    )
    broken.write_text(
        json.dumps(
            {
                **base,
                "model": "broken",
                "ranking_eligible": False,
                "selection_score": None,
                "cases_completed": 10,
                "cases_failed": 1,
            }
        ),
        encoding="utf-8",
    )
    rows = compare_summaries([broken, eligible])
    assert rows[0]["model"] == "eligible"
    assert rows[1]["selection_score"] is None
