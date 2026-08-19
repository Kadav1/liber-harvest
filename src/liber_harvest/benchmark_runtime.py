"""v0.1.7 benchmark runtime with preflight and ranking-safe failure handling."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Iterable

import httpx

from .adapters.exegate.loader import ExegateAdapter
from .benchmark import (
    BENCHMARK_VERSION,
    BenchmarkCase,
    InstrumentedProvider,
    _benchmark_id,
    _read_run_payload,
    _slug,
    resolve_case_source,
    score_case,
    select_cases,
)
from .constants import CONTRACT_VERSION, EXTRACTOR_VERSION
from .jsonutil import ModelResponseError
from .pipeline import HarvestContractError, LiberHarvester
from .providers.base import ExtractionProvider
from .providers.lmstudio import LMStudioHTTPError
from .storage.jsonl import atomic_write, json_bytes

SCORABLE_FAILURES = {"contract_failed", "model_failed"}
INFRASTRUCTURE_FAILURES = {"infrastructure_failed", "source_missing"}
SESSION_MODE = "stateless"
SEMANTIC_CALL_CAP = 2


class BenchmarkPreflightError(RuntimeError):
    """Raised before inference when the suite cannot be executed fairly."""


def preflight_benchmark(
    *,
    provider: ExtractionProvider,
    cases: list[BenchmarkCase],
    corpus_root: Path,
) -> tuple[dict[str, Path], dict[str, Any]]:
    """Validate every source and provider prerequisite before spending model time."""
    adapter = ExegateAdapter()
    sources: dict[str, Path] = {}
    problems: list[str] = []
    for case in cases:
        try:
            source_path = resolve_case_source(case, corpus_root)
            adapter.load(source_path)
            sources[case.case_id] = source_path
        except Exception as exc:
            problems.append(f"{case.case_id}: {exc}")

    provider_meta: dict[str, Any] = {}
    preflight = getattr(provider, "benchmark_preflight", None)
    if callable(preflight):
        try:
            value = preflight()
            if isinstance(value, dict):
                provider_meta = value
        except Exception as exc:
            problems.append(f"provider: {exc}")

    if problems:
        joined = "\n".join(f"- {problem}" for problem in problems)
        raise BenchmarkPreflightError(
            "Benchmark preflight failed before inference. Correct these issues and rerun:\n"
            + joined
        )
    return sources, provider_meta


def _failure_status(exc: Exception) -> str:
    if isinstance(exc, FileNotFoundError):
        return "source_missing"
    if isinstance(exc, HarvestContractError):
        return "contract_failed"
    if isinstance(exc, ModelResponseError):
        return "model_failed"
    if isinstance(
        exc,
        (
            LMStudioHTTPError,
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.HTTPStatusError,
        ),
    ):
        return "infrastructure_failed"
    return "infrastructure_failed"


def _failure_payload(
    *,
    case: BenchmarkCase,
    exc: Exception,
    instrumented: InstrumentedProvider,
    elapsed_seconds: float,
) -> dict[str, Any]:
    status = _failure_status(exc)
    scorable = status in SCORABLE_FAILURES
    return {
        "benchmark_version": BENCHMARK_VERSION,
        "contract_version": CONTRACT_VERSION,
        "extractor_version": EXTRACTOR_VERSION,
        "case_id": case.case_id,
        "historical_source_key": case.historical_source_key,
        "purpose": case.purpose,
        "targets": list(case.targets),
        "status": status,
        "session_mode": SESSION_MODE,
        "ranking_scorable": scorable,
        "compliance_score": 0.0 if scorable else None,
        "target_checks": [],
        "target_pass_rate": 0.0 if scorable else None,
        "failure": {
            "type": type(exc).__name__,
            "message": str(exc),
            "contract_error": isinstance(exc, HarvestContractError),
        },
        "metrics": {
            "provider": instrumented.metrics.snapshot(),
            "elapsed_seconds": round(elapsed_seconds, 6),
        },
    }


def run_model_benchmark(
    *,
    provider: ExtractionProvider,
    provider_name: str,
    model_label: str,
    corpus_root: Path = Path("data"),
    calibration_root: Path = Path("calibration"),
    case_ids: Iterable[str] | None = None,
    out_root: Path = Path("benchmark-results"),
    max_repairs: int = 1,
    configuration: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], Path]:
    if max_repairs not in {0, 1}:
        raise ValueError("v0.1.7 benchmark permits --max-repairs 0 or 1")
    cases = select_cases(case_ids, calibration_root)
    if not cases:
        raise ValueError(f"No calibration cases found under {calibration_root}")

    resolved_sources, provider_preflight = preflight_benchmark(
        provider=provider,
        cases=cases,
        corpus_root=corpus_root,
    )

    benchmark_id = _benchmark_id()
    suite_dir = out_root / f"{benchmark_id}-{_slug(provider_name)}-{_slug(model_label)}"
    suite_dir.mkdir(parents=True, exist_ok=True)

    instrumented = InstrumentedProvider(provider)
    harvester = LiberHarvester(instrumented, max_repairs=max_repairs)
    results: list[dict[str, Any]] = []

    for case in cases:
        case_dir = suite_dir / case.case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        instrumented.metrics.reset()
        started = time.perf_counter()
        try:
            source_path = resolved_sources[case.case_id]
            execution = harvester.run(
                source_path,
                out_root=case_dir / "harvest",
                write_library=False,
            )
            metrics = instrumented.metrics.snapshot()
            semantic_calls = int(metrics["extract_calls"]) + int(metrics["repair_calls"])
            if semantic_calls > SEMANTIC_CALL_CAP:
                raise RuntimeError(
                    f"Semantic provider call cap exceeded: {semantic_calls} > {SEMANTIC_CALL_CAP}"
                )
            run_payload = _read_run_payload(execution.manifest.artifacts.run_json.path)
            result = score_case(
                case=case,
                fragments=list(execution.fragments),
                run_payload=run_payload,
                provider_metrics=metrics,
                elapsed_seconds=time.perf_counter() - started,
            )
            result["source_path"] = str(source_path)
            result["harvest_run_id"] = execution.run_id
            result["session_mode"] = SESSION_MODE
            result["ranking_scorable"] = True
        except Exception as exc:
            result = _failure_payload(
                case=case,
                exc=exc,
                instrumented=instrumented,
                elapsed_seconds=time.perf_counter() - started,
            )
        atomic_write(case_dir / "result.json", json_bytes(result))
        results.append(result)

    requested_count = len(results)
    completed = [result for result in results if result["status"] == "completed"]
    scorable = [
        result
        for result in results
        if result["status"] == "completed" or result["status"] in SCORABLE_FAILURES
    ]
    infrastructure_failures = [
        result for result in results if result["status"] in INFRASTRUCTURE_FAILURES
    ]
    ranking_eligible = not infrastructure_failures and len(scorable) == requested_count

    mean_compliance = (
        sum(float(result.get("compliance_score") or 0.0) for result in scorable)
        / len(scorable)
        if scorable
        else 0.0
    )
    scored_target_checks = [
        check
        for result in completed
        for check in result.get("target_checks", [])
        if check.get("status") in {"pass", "fail"}
    ]
    target_pass_pct = (
        100.0
        * sum(check["status"] == "pass" for check in scored_target_checks)
        / len(scored_target_checks)
        if scored_target_checks
        else 0.0
    )
    selection_score = (
        round((0.8 * mean_compliance) + (0.2 * target_pass_pct), 3)
        if ranking_eligible
        else None
    )

    status_counts = {
        status: sum(result["status"] == status for result in results)
        for status in {
            "completed",
            "contract_failed",
            "model_failed",
            "infrastructure_failed",
            "source_missing",
        }
    }
    config = dict(configuration or {})
    config.update(
        {
            "session_mode": SESSION_MODE,
            "semantic_call_cap": SEMANTIC_CALL_CAP,
            "provider_preflight": provider_preflight,
        }
    )

    summary = {
        "benchmark_version": BENCHMARK_VERSION,
        "contract_version": CONTRACT_VERSION,
        "extractor_version": EXTRACTOR_VERSION,
        "benchmark_id": benchmark_id,
        "provider": provider_name,
        "model": model_label,
        "configuration": config,
        "benchmark_valid": ranking_eligible,
        "ranking_eligible": ranking_eligible,
        "cases_requested": requested_count,
        "cases_completed": len(completed),
        "cases_failed": requested_count - len(completed),
        "status_counts": status_counts,
        "mean_compliance_score": round(mean_compliance, 3),
        "target_checks_scored": len(scored_target_checks),
        "target_pass_pct": round(target_pass_pct, 3),
        "selection_score": selection_score,
        "total_repair_calls": sum(
            int(result.get("metrics", {}).get("provider", {}).get("repair_calls", 0))
            for result in results
        ),
        "total_semantic_seconds": round(
            sum(
                float(
                    result.get("metrics", {})
                    .get("provider", {})
                    .get("semantic_seconds", 0.0)
                )
                for result in results
            ),
            6,
        ),
        "total_elapsed_seconds": round(
            sum(float(result.get("metrics", {}).get("elapsed_seconds", 0.0)) for result in results),
            6,
        ),
        "case_results": [
            {
                "case_id": result["case_id"],
                "status": result["status"],
                "ranking_scorable": result.get("ranking_scorable", False),
                "compliance_score": result.get("compliance_score"),
                "target_pass_rate": result.get("target_pass_rate"),
                "result_path": f"{result['case_id']}/result.json",
            }
            for result in results
        ],
        "manual_semantic_review_required": True,
        "ranking_note": (
            "selection_score = 80% mean deterministic compliance + 20% target-check pass percentage. "
            "Infrastructure/source failures invalidate ranking rather than scoring the model as zero. "
            "Informational semantic targets remain excluded from automatic scoring."
        ),
    }
    summary_path = suite_dir / "summary.json"
    atomic_write(summary_path, json_bytes(summary))
    return summary, summary_path


def load_summary(path: Path) -> dict[str, Any]:
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("benchmark_version") != BENCHMARK_VERSION:
        raise ValueError(f"Not a {BENCHMARK_VERSION} summary: {path}")
    return data


def compare_summaries(paths: Iterable[Path]) -> list[dict[str, Any]]:
    rows = []
    for path in paths:
        summary = load_summary(path)
        score = summary.get("selection_score")
        rows.append(
            {
                "path": str(path),
                "provider": summary.get("provider"),
                "model": summary.get("model"),
                "ranking_eligible": bool(summary.get("ranking_eligible", False)),
                "selection_score": float(score) if score is not None else None,
                "mean_compliance_score": float(summary.get("mean_compliance_score", 0.0)),
                "target_pass_pct": float(summary.get("target_pass_pct", 0.0)),
                "cases_completed": int(summary.get("cases_completed", 0)),
                "cases_requested": int(summary.get("cases_requested", 0)),
                "cases_failed": int(summary.get("cases_failed", 0)),
                "repair_calls": int(summary.get("total_repair_calls", 0)),
                "semantic_seconds": float(summary.get("total_semantic_seconds", 0.0)),
            }
        )
    rows.sort(
        key=lambda row: (
            row["ranking_eligible"],
            row["selection_score"] if row["selection_score"] is not None else -1.0,
            row["mean_compliance_score"],
            row["target_pass_pct"],
            -row["repair_calls"],
            -row["semantic_seconds"],
        ),
        reverse=True,
    )
    return rows
