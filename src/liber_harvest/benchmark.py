"""Model-selection benchmark for the frozen T01-T11 calibration corpus."""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .adapters.exegate.loader import ExegateAdapter
from .constants import CONTRACT_VERSION, EXTRACTOR_VERSION, PIPELINE_WRAPPER_MARKERS
from .models import DerivationOperation, LoreFragmentRecord, ProvenancePrecision, ReviewReason
from .pipeline import HarvestContractError, LiberHarvester
from .providers.base import ExtractionProvider
from .storage.jsonl import atomic_write, json_bytes

BENCHMARK_VERSION = "model-selection/0.1"

SCORE_WEIGHTS = {
    "contract": 25.0,
    "coverage": 20.0,
    "provenance": 15.0,
    "modality_evidence": 15.0,
    "legacy_isolation": 10.0,
    "dedupe": 5.0,
    "review_burden": 5.0,
    "wrapper_isolation": 5.0,
}


@dataclass
class ProviderMetrics:
    extract_calls: int = 0
    repair_calls: int = 0
    semantic_seconds: float = 0.0

    def reset(self) -> None:
        self.extract_calls = 0
        self.repair_calls = 0
        self.semantic_seconds = 0.0

    def snapshot(self) -> dict[str, Any]:
        return {
            "extract_calls": self.extract_calls,
            "repair_calls": self.repair_calls,
            "semantic_seconds": round(self.semantic_seconds, 6),
        }


class InstrumentedProvider:
    """Wrap any extraction provider without changing its semantics."""

    def __init__(self, inner: ExtractionProvider):
        self.inner = inner
        self.metrics = ProviderMetrics()

    def extract(self, envelope):
        started = time.perf_counter()
        try:
            return self.inner.extract(envelope)
        finally:
            self.metrics.extract_calls += 1
            self.metrics.semantic_seconds += time.perf_counter() - started

    def repair(self, candidate, validation_errors, envelope):
        started = time.perf_counter()
        try:
            return self.inner.repair(candidate, validation_errors, envelope)
        finally:
            self.metrics.repair_calls += 1
            self.metrics.semantic_seconds += time.perf_counter() - started


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    historical_source_key: str
    purpose: str
    targets: tuple[str, ...]
    status: str
    source_distribution: str
    contract_version: str

    @classmethod
    def from_path(cls, path: Path) -> "BenchmarkCase":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            case_id=str(data["case_id"]),
            historical_source_key=str(data["historical_source_key"]),
            purpose=str(data["purpose"]),
            targets=tuple(str(x) for x in data.get("targets", [])),
            status=str(data.get("status", "calibration")),
            source_distribution=str(data.get("source_distribution", "external-legacy-corpus")),
            contract_version=str(data["contract_version"]),
        )


def discover_cases(calibration_root: Path = Path("calibration")) -> list[BenchmarkCase]:
    cases: list[BenchmarkCase] = []
    for case_path in sorted(calibration_root.glob("T[0-9][0-9]/case.json")):
        case = BenchmarkCase.from_path(case_path)
        if case.contract_version != CONTRACT_VERSION:
            raise ValueError(
                f"{case.case_id} targets {case.contract_version}, expected {CONTRACT_VERSION}"
            )
        cases.append(case)
    return cases


def select_cases(
    requested: Iterable[str] | None,
    calibration_root: Path = Path("calibration"),
) -> list[BenchmarkCase]:
    available = {case.case_id: case for case in discover_cases(calibration_root)}
    if not requested:
        return [available[key] for key in sorted(available)]
    selected = []
    for raw in requested:
        key = raw.strip().upper()
        if key not in available:
            raise ValueError(
                f"Unknown calibration case {raw!r}; available: {', '.join(sorted(available))}"
            )
        selected.append(available[key])
    return selected


def resolve_case_source(case: BenchmarkCase, corpus_root: Path = Path("data")) -> Path:
    root = corpus_root.expanduser()
    key = case.historical_source_key
    if key.startswith("song_"):
        candidates = [root / "parsed" / f"{key}.json", root / f"{key}.json"]
    else:
        candidates = [
            root / "bundles" / key,
            root / "bundles" / key / "exegate_run.json",
            root / key,
            root / key / "exegate_run.json",
        ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    rendered = ", ".join(str(path) for path in candidates)
    raise FileNotFoundError(
        f"{case.case_id} source {key!r} not found. Checked: {rendered}"
    )


def _read_run_payload(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Benchmark run payload is not an object: {path}")
    return payload


def _binding_leaks(fragment: LoreFragmentRecord) -> list[str]:
    normalized = fragment.content.normalized_lore.casefold()
    leaks: list[str] = []
    for binding in fragment.legacy_bindings:
        if binding.handling.value not in {"generalized", "removed_from_normalized"}:
            continue
        needle = binding.value.strip().casefold()
        if needle and needle in normalized:
            leaks.append(binding.value)
    return sorted(set(leaks))


def _wrapper_leaks(fragment: LoreFragmentRecord) -> list[str]:
    haystack = f"{fragment.title}\n{fragment.content.normalized_lore}".casefold()
    return [
        marker
        for marker in PIPELINE_WRAPPER_MARKERS
        if marker.casefold() in haystack
    ]


def _normalized_key(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().casefold())


def _target_checks(
    targets: Iterable[str],
    fragments: list[LoreFragmentRecord],
    run_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    precisions = [
        anchor.precision.value
        for fragment in fragments
        for anchor in fragment.provenance
    ]
    evidence_layers = {
        anchor.evidence_layer.value
        for fragment in fragments
        for anchor in fragment.provenance
    }
    types = {fragment.type.value for fragment in fragments}
    legacy_leaks = [
        leak for fragment in fragments for leak in _binding_leaks(fragment)
    ]
    wrapper_leaks = [
        leak for fragment in fragments for leak in _wrapper_leaks(fragment)
    ]

    def add(target: str, status: str, detail: str, value: Any = None) -> None:
        checks.append(
            {"target": target, "status": status, "detail": detail, "value": value}
        )

    for target in sorted(set(targets)):
        if target in {
            "empty_array_resilience",
            "broken_source_resilience",
            "null_id_resilience",
        }:
            add(target, "pass", "case completed through deterministic materialization")
        elif target in {"lf13", "span_materialization"}:
            if target == "span_materialization":
                count = precisions.count(ProvenancePrecision.SPAN.value)
                add(
                    target,
                    "pass" if count > 0 else "fail",
                    "requires at least one precision=span provenance anchor",
                    count,
                )
            else:
                add(target, "pass", "materialized provenance self-check completed")
        elif target == "lf14":
            add(target, "pass", "derivation operations passed frozen model validation")
        elif target == "lf15_modality":
            add(
                target,
                "pass",
                "claim/source modality constraints passed frozen model validation",
            )
        elif target in {"lf16", "lf16_evidence_layers", "evidence_layer_separation"}:
            add(
                target,
                "pass" if evidence_layers else "fail",
                "evidence layers present on materialized provenance",
                sorted(evidence_layers),
            )
        elif target in {"legacy_bindings", "legacy_normalization"}:
            add(
                target,
                "pass" if not legacy_leaks else "fail",
                "generalized/removed legacy bindings must not leak into normalized lore",
                sorted(set(legacy_leaks)),
            )
        elif target == "pipeline_wrapper_stripping":
            add(
                target,
                "pass" if not wrapper_leaks else "fail",
                "pipeline wrapper markers absent from normalized lore",
                sorted(set(wrapper_leaks)),
            )
        elif target == "intra_source_dedupe":
            normalized = [
                _normalized_key(fragment.content.normalized_lore)
                for fragment in fragments
            ]
            duplicates = len(normalized) - len(set(normalized))
            add(
                target,
                "pass" if duplicates == 0 else "fail",
                "exact normalized-lore duplicates",
                duplicates,
            )
        elif target == "merged_intra_source":
            count = sum(
                DerivationOperation.MERGED_INTRA_SOURCE
                in fragment.derivation.operations
                for fragment in fragments
            )
            add(
                target,
                "pass" if count > 0 else "fail",
                "fragments using merged_intra_source",
                count,
            )
        elif target == "sensory_palette":
            count = sum(
                fragment.type.value == "sensory_palette" for fragment in fragments
            )
            add(
                target,
                "pass" if count > 0 else "fail",
                "sensory_palette fragments",
                count,
            )
        elif target == "structured_objects":
            pointers = [
                anchor.json_pointer
                for fragment in fragments
                for anchor in fragment.provenance
            ]
            count = sum(
                pointer.startswith("/symbols/") or pointer.startswith("/rituals/")
                for pointer in pointers
            )
            add(
                target,
                "pass" if count > 0 else "fail",
                "anchors into structured symbols/rituals",
                count,
            )
        elif target in {"semantic_recall", "decomposition"}:
            unparseable = sum(
                entry.get("disposition") == "unparseable"
                for entry in run_payload.get("coverage", [])
            )
            add(
                target,
                "pass" if fragments and unparseable == 0 else "fail",
                "proxy check: non-empty yield and no unparseable coverage entries",
                {"fragments": len(fragments), "unparseable": unparseable},
            )
        elif target == "taxonomy":
            add(
                target,
                "informational",
                "schema-valid taxonomy; compare diversity rather than maximizing it",
                {"types": sorted(types), "type_count": len(types)},
            )
        elif target in {
            "name_restraint",
            "seed_phrase_restraint",
            "contradiction_preservation",
        }:
            if target == "name_restraint":
                value = sum(fragment.type.value == "name" for fragment in fragments)
            elif target == "seed_phrase_restraint":
                value = sum(fragment.type.value == "phrase" for fragment in fragments)
            else:
                value = sum(
                    hint.relation.value == "contradicts"
                    for fragment in fragments
                    for hint in fragment.relation_hints
                )
            add(
                target,
                "informational",
                "requires semantic/gold review; reported but not automatically scored",
                value,
            )
        else:
            add(
                target,
                "informational",
                "no deterministic target-specific assertion defined",
                None,
            )
    return checks


def score_case(
    *,
    case: BenchmarkCase,
    fragments: list[LoreFragmentRecord],
    run_payload: dict[str, Any],
    provider_metrics: dict[str, Any],
    elapsed_seconds: float,
) -> dict[str, Any]:
    review_count = sum(fragment.review.required for fragment in fragments)
    review_ratio = review_count / len(fragments) if fragments else 1.0

    precision_reasons = {
        ReviewReason.PROVENANCE_PRECISION_REDUCED.value,
        ReviewReason.PROVENANCE_SPAN_AMBIGUOUS.value,
        ReviewReason.PROVENANCE_EXCERPT_UNRESOLVED.value,
    }
    provenance_review_count = sum(
        1
        for fragment in fragments
        if any(reason.value in precision_reasons for reason in fragment.review.reasons)
    )

    coverage = run_payload.get("coverage", [])
    unparseable = sum(
        entry.get("disposition") == "unparseable" for entry in coverage
    )
    coverage_factor = (
        1.0
        if not coverage
        else max(0.0, 1.0 - (unparseable / len(coverage)))
    )

    legacy_leaks = [
        {"fragment_id": fragment.fragment_id, "binding": leak}
        for fragment in fragments
        for leak in _binding_leaks(fragment)
    ]
    legacy_binding_count = sum(
        binding.handling.value in {"generalized", "removed_from_normalized"}
        for fragment in fragments
        for binding in fragment.legacy_bindings
    )
    legacy_factor = 1.0
    if legacy_binding_count:
        legacy_factor = max(
            0.0, 1.0 - (len(legacy_leaks) / legacy_binding_count)
        )

    normalized = [
        _normalized_key(fragment.content.normalized_lore) for fragment in fragments
    ]
    duplicate_count = len(normalized) - len(set(normalized))
    dedupe_factor = (
        1.0
        if not fragments
        else max(0.0, 1.0 - duplicate_count / len(fragments))
    )

    wrapper_leaks = [
        {"fragment_id": fragment.fragment_id, "marker": leak}
        for fragment in fragments
        for leak in _wrapper_leaks(fragment)
    ]
    wrapper_factor = (
        1.0
        if not wrapper_leaks
        else max(0.0, 1.0 - len(wrapper_leaks) / max(1, len(fragments)))
    )
    provenance_factor = (
        1.0
        if not fragments
        else max(0.0, 1.0 - provenance_review_count / len(fragments))
    )

    components = {
        "contract": SCORE_WEIGHTS["contract"],
        "coverage": SCORE_WEIGHTS["coverage"] * coverage_factor,
        "provenance": SCORE_WEIGHTS["provenance"] * provenance_factor,
        "modality_evidence": SCORE_WEIGHTS["modality_evidence"],
        "legacy_isolation": SCORE_WEIGHTS["legacy_isolation"] * legacy_factor,
        "dedupe": SCORE_WEIGHTS["dedupe"] * dedupe_factor,
        "review_burden": SCORE_WEIGHTS["review_burden"] * (1.0 - review_ratio),
        "wrapper_isolation": SCORE_WEIGHTS["wrapper_isolation"] * wrapper_factor,
    }
    compliance_score = round(sum(components.values()), 3)

    target_checks = _target_checks(case.targets, fragments, run_payload)
    scored_targets = [
        check for check in target_checks if check["status"] in {"pass", "fail"}
    ]
    target_pass_rate = (
        sum(check["status"] == "pass" for check in scored_targets)
        / len(scored_targets)
        if scored_targets
        else None
    )

    anchors = [
        anchor for fragment in fragments for anchor in fragment.provenance
    ]
    return {
        "benchmark_version": BENCHMARK_VERSION,
        "contract_version": CONTRACT_VERSION,
        "extractor_version": EXTRACTOR_VERSION,
        "case_id": case.case_id,
        "historical_source_key": case.historical_source_key,
        "purpose": case.purpose,
        "targets": list(case.targets),
        "status": "completed",
        "compliance_score": compliance_score,
        "score_components": {
            key: round(value, 3) for key, value in components.items()
        },
        "target_checks": target_checks,
        "target_pass_rate": (
            round(target_pass_rate, 6) if target_pass_rate is not None else None
        ),
        "metrics": {
            "fragments": len(fragments),
            "review_required": review_count,
            "review_ratio": round(review_ratio, 6),
            "coverage_entries": len(coverage),
            "unparseable_coverage": unparseable,
            "legacy_binding_leaks": legacy_leaks,
            "wrapper_leaks": wrapper_leaks,
            "exact_duplicate_normalized_lore": duplicate_count,
            "types": sorted({fragment.type.value for fragment in fragments}),
            "domains": sorted(
                {domain for fragment in fragments for domain in fragment.domains}
            ),
            "modalities": sorted(
                {fragment.claim.modality.value for fragment in fragments}
            ),
            "evidence_layers": sorted(
                {anchor.evidence_layer.value for anchor in anchors}
            ),
            "provenance_precision": {
                precision.value: sum(
                    anchor.precision == precision for anchor in anchors
                )
                for precision in ProvenancePrecision
            },
            "provider": provider_metrics,
            "elapsed_seconds": round(elapsed_seconds, 6),
        },
    }


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-._").lower()
    return cleaned or "model"


def _benchmark_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"BMS-{stamp}"


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
    cases = select_cases(case_ids, calibration_root)
    if not cases:
        raise ValueError(f"No calibration cases found under {calibration_root}")

    benchmark_id = _benchmark_id()
    suite_dir = (
        out_root
        / f"{benchmark_id}-{_slug(provider_name)}-{_slug(model_label)}"
    )
    suite_dir.mkdir(parents=True, exist_ok=True)

    instrumented = InstrumentedProvider(provider)
    harvester = LiberHarvester(instrumented, max_repairs=max_repairs)
    adapter = ExegateAdapter()
    results: list[dict[str, Any]] = []

    for case in cases:
        case_dir = suite_dir / case.case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        instrumented.metrics.reset()
        started = time.perf_counter()
        try:
            source_path = resolve_case_source(case, corpus_root)
            adapter.load(source_path)
            execution = harvester.run(
                source_path,
                out_root=case_dir / "harvest",
                write_library=False,
            )
            run_payload = _read_run_payload(
                execution.manifest.artifacts.run_json.path
            )
            result = score_case(
                case=case,
                fragments=list(execution.fragments),
                run_payload=run_payload,
                provider_metrics=instrumented.metrics.snapshot(),
                elapsed_seconds=time.perf_counter() - started,
            )
            result["source_path"] = str(source_path)
            result["harvest_run_id"] = execution.run_id
        except Exception as exc:
            result = {
                "benchmark_version": BENCHMARK_VERSION,
                "contract_version": CONTRACT_VERSION,
                "extractor_version": EXTRACTOR_VERSION,
                "case_id": case.case_id,
                "historical_source_key": case.historical_source_key,
                "purpose": case.purpose,
                "targets": list(case.targets),
                "status": "failed",
                "compliance_score": 0.0,
                "target_checks": [],
                "target_pass_rate": 0.0,
                "failure": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "contract_error": isinstance(exc, HarvestContractError),
                },
                "metrics": {
                    "provider": instrumented.metrics.snapshot(),
                    "elapsed_seconds": round(
                        time.perf_counter() - started, 6
                    ),
                },
            }
        atomic_write(case_dir / "result.json", json_bytes(result))
        results.append(result)

    completed = [
        result for result in results if result["status"] == "completed"
    ]
    requested_count = len(results)
    mean_compliance = (
        sum(float(result["compliance_score"]) for result in results)
        / requested_count
        if requested_count
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
    selection_score = round(
        (0.8 * mean_compliance) + (0.2 * target_pass_pct), 3
    )

    summary = {
        "benchmark_version": BENCHMARK_VERSION,
        "contract_version": CONTRACT_VERSION,
        "extractor_version": EXTRACTOR_VERSION,
        "benchmark_id": benchmark_id,
        "provider": provider_name,
        "model": model_label,
        "configuration": configuration or {},
        "cases_requested": requested_count,
        "cases_completed": len(completed),
        "cases_failed": requested_count - len(completed),
        "mean_compliance_score": round(mean_compliance, 3),
        "target_checks_scored": len(scored_target_checks),
        "target_pass_pct": round(target_pass_pct, 3),
        "selection_score": selection_score,
        "total_repair_calls": sum(
            int(
                result.get("metrics", {})
                .get("provider", {})
                .get("repair_calls", 0)
            )
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
            sum(
                float(result.get("metrics", {}).get("elapsed_seconds", 0.0))
                for result in results
            ),
            6,
        ),
        "case_results": [
            {
                "case_id": result["case_id"],
                "status": result["status"],
                "compliance_score": result["compliance_score"],
                "target_pass_rate": result.get("target_pass_rate"),
                "result_path": f"{result['case_id']}/result.json",
            }
            for result in results
        ],
        "manual_semantic_review_required": True,
        "ranking_note": (
            "selection_score = 80% mean deterministic compliance + 20% "
            "target-check pass percentage. Informational semantic targets are "
            "deliberately excluded from automatic scoring. Use the automatic "
            "score to shortlist models, then inspect semantic yield before final selection."
        ),
    }
    summary_path = suite_dir / "summary.json"
    atomic_write(summary_path, json_bytes(summary))
    return summary, summary_path


def load_summary(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("benchmark_version") != BENCHMARK_VERSION:
        raise ValueError(f"Not a {BENCHMARK_VERSION} summary: {path}")
    return data


def compare_summaries(paths: Iterable[Path]) -> list[dict[str, Any]]:
    rows = []
    for path in paths:
        summary = load_summary(path)
        rows.append(
            {
                "path": str(path),
                "provider": summary.get("provider"),
                "model": summary.get("model"),
                "selection_score": float(summary.get("selection_score", 0.0)),
                "mean_compliance_score": float(
                    summary.get("mean_compliance_score", 0.0)
                ),
                "target_pass_pct": float(summary.get("target_pass_pct", 0.0)),
                "cases_completed": int(summary.get("cases_completed", 0)),
                "cases_requested": int(summary.get("cases_requested", 0)),
                "cases_failed": int(summary.get("cases_failed", 0)),
                "repair_calls": int(summary.get("total_repair_calls", 0)),
                "semantic_seconds": float(
                    summary.get("total_semantic_seconds", 0.0)
                ),
            }
        )
    rows.sort(
        key=lambda row: (
            row["cases_completed"] == row["cases_requested"],
            row["selection_score"],
            row["mean_compliance_score"],
            row["target_pass_pct"],
            -row["repair_calls"],
            -row["semantic_seconds"],
        ),
        reverse=True,
    )
    return rows
