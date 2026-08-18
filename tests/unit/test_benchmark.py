import json
from pathlib import Path

from liber_harvest.benchmark import (
    BenchmarkCase,
    InstrumentedProvider,
    compare_summaries,
    discover_cases,
    resolve_case_source,
)


class DummyProvider:
    def extract(self, envelope):
        del envelope
        return {"ok": True}

    def repair(self, candidate, validation_errors, envelope):
        del validation_errors, envelope
        return candidate


def test_instrumented_provider_counts_extract_and_repair():
    provider = InstrumentedProvider(DummyProvider())
    assert provider.extract(object()) == {"ok": True}
    assert provider.repair({"ok": True}, "error", object()) == {"ok": True}
    metrics = provider.metrics.snapshot()
    assert metrics["extract_calls"] == 1
    assert metrics["repair_calls"] == 1
    assert metrics["semantic_seconds"] >= 0


def test_discover_cases_reads_ordered_case_files(tmp_path: Path):
    for case_id, source in (("T02", "EXE-BUNDLE-V-N-01"), ("T01", "song_006")):
        case_dir = tmp_path / case_id
        case_dir.mkdir()
        (case_dir / "case.json").write_text(
            json.dumps(
                {
                    "case_id": case_id,
                    "historical_source_key": source,
                    "purpose": "test",
                    "targets": ["semantic_recall"],
                    "status": "calibration",
                    "source_distribution": "external-legacy-corpus",
                    "contract_version": "exegate-harvest/0.1.2",
                }
            ),
            encoding="utf-8",
        )
    cases = discover_cases(tmp_path)
    assert [case.case_id for case in cases] == ["T01", "T02"]


def test_resolve_case_source_uses_runtime_convention(tmp_path: Path):
    parsed = tmp_path / "parsed"
    parsed.mkdir()
    source = parsed / "song_006.json"
    source.write_text("{}", encoding="utf-8")
    case = BenchmarkCase(
        case_id="T01",
        historical_source_key="song_006",
        purpose="test",
        targets=("semantic_recall",),
        status="calibration",
        source_distribution="external-legacy-corpus",
        contract_version="exegate-harvest/0.1.2",
    )
    assert resolve_case_source(case, tmp_path) == source


def test_compare_summaries_prefers_complete_higher_score(tmp_path: Path):
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    common = {
        "benchmark_version": "model-selection/0.1",
        "provider": "lmstudio",
        "cases_requested": 11,
        "target_pass_pct": 100.0,
        "total_repair_calls": 0,
        "total_semantic_seconds": 10.0,
    }
    a.write_text(
        json.dumps(
            {
                **common,
                "model": "model-a",
                "selection_score": 90.0,
                "mean_compliance_score": 90.0,
                "cases_completed": 11,
                "cases_failed": 0,
            }
        ),
        encoding="utf-8",
    )
    b.write_text(
        json.dumps(
            {
                **common,
                "model": "model-b",
                "selection_score": 99.0,
                "mean_compliance_score": 99.0,
                "cases_completed": 10,
                "cases_failed": 1,
            }
        ),
        encoding="utf-8",
    )
    rows = compare_summaries([b, a])
    assert rows[0]["model"] == "model-a"
