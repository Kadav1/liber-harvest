"""High-level Liber Harvest orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from .providers.base import ExtractionProvider
from .constants import EXTRACTOR_VERSION
from .corrections import (
    apply_deterministic_corrections,
    fragment_error_indices,
    make_fragment_repair_subset,
    merge_fragment_repair,
)
from .exporter import export_harvest
from .materializer import materialize_fragment
from .models import ExegateHarvestResult, HarvestManifest, HarvestSourceRef, LoreFragmentRecord
from .adapters.base import SourceAdapter
from .adapters.exegate.loader import ExegateAdapter
from .validation import (
    ValidationIssue, validate_materialized_record, validate_result_against_source,
)


class HarvestContractError(ValueError):
    def __init__(self, message: str, *, issues: list[ValidationIssue] | None = None):
        super().__init__(message)
        self.issues = issues or []


@dataclass(frozen=True)
class HarvestExecution:
    source_path: Path
    run_id: str
    fragments: tuple[LoreFragmentRecord, ...]
    manifest: HarvestManifest


class LiberHarvester:
    """Run one source through extraction, deterministic correction, and materialization.

    v0.1.7 caps semantic provider invocations at one extraction plus at most one
    fragment-scoped repair. Deterministic source-validation failures are never sent
    back to the model as a full-result repair prompt.
    """

    def __init__(
        self,
        provider: ExtractionProvider,
        *,
        adapter: SourceAdapter | None = None,
        max_repairs: int = 1,
    ):
        if max_repairs not in {0, 1}:
            raise ValueError("Liber Harvest v0.1.7 supports max_repairs=0 or 1")
        self.provider = provider
        self.adapter = adapter or ExegateAdapter()
        self.max_repairs = max_repairs

    @staticmethod
    def make_run_id(source_sha256: str) -> str:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        return f"LHR-{stamp}-{source_sha256[:8].upper()}"

    @staticmethod
    def _format_validation_errors(exc: ValidationError, indices: tuple[int, ...]) -> str:
        selected = []
        for error in exc.errors():
            loc = error.get("loc", ())
            if len(loc) >= 2 and loc[0] == "fragments" and loc[1] in indices:
                selected.append(error)
        return "\n".join(
            f"{'.'.join(str(part) for part in error.get('loc', ()))}: {error.get('msg', 'validation error')}"
            for error in selected
        )

    def _extract_and_validate(self, envelope) -> ExegateHarvestResult:
        candidate = self.provider.extract(envelope)
        candidate, _ = apply_deterministic_corrections(candidate, envelope)
        try:
            return ExegateHarvestResult.model_validate(candidate)
        except ValidationError as exc:
            if self.max_repairs == 0:
                raise HarvestContractError(
                    f"Extractor output failed v0.1.2 schema validation after deterministic correction: {exc}"
                ) from exc

            indices = fragment_error_indices(exc)
            subset = make_fragment_repair_subset(candidate, indices)
            if subset is None:
                raise HarvestContractError(
                    "Extractor output failed v0.1.2 schema validation outside fragment scope; "
                    "v0.1.7 will not send the full result back to the model for repair: "
                    f"{exc}"
                ) from exc

            repair_errors = self._format_validation_errors(exc, indices)
            repaired_subset = self.provider.repair(subset, repair_errors, envelope)
            repaired_subset, _ = apply_deterministic_corrections(repaired_subset, envelope)
            try:
                ExegateHarvestResult.model_validate(repaired_subset)
            except ValidationError as repair_exc:
                raise HarvestContractError(
                    "Fragment-scoped repair failed v0.1.2 schema validation: "
                    f"{repair_exc}"
                ) from repair_exc

            merged = merge_fragment_repair(candidate, indices, repaired_subset)
            merged, _ = apply_deterministic_corrections(merged, envelope)
            try:
                return ExegateHarvestResult.model_validate(merged)
            except ValidationError as merged_exc:
                raise HarvestContractError(
                    "Extractor output remained invalid after one fragment-scoped repair: "
                    f"{merged_exc}"
                ) from merged_exc

    def run(
        self,
        source_path: Path,
        *,
        out_root: Path = Path("harvest"),
        run_id: str | None = None,
        write_library: bool = True,
    ) -> HarvestExecution:
        loaded = self.adapter.load(source_path)
        envelope, source_document, bundle_id = loaded.envelope, loaded.document, loaded.bundle_id
        result = self._extract_and_validate(envelope)

        issues = validate_result_against_source(
            result,
            source_path=envelope.source_path,
            source_sha256=envelope.source_sha256,
            source_document=source_document,
        )
        if issues:
            formatted = "\n".join(f"[{issue.code}] {issue.message}" for issue in issues)
            raise HarvestContractError(
                "Harvest result failed deterministic validation; deterministic failures are "
                "not delegated back to the model in v0.1.7:\n" + formatted,
                issues=issues,
            )

        actual_run_id = run_id or self.make_run_id(envelope.source_sha256)
        fragments = [
            materialize_fragment(
                fragment,
                source_document=source_document,
                run_id=actual_run_id,
                extractor_version=EXTRACTOR_VERSION,
            )
            for fragment in result.fragments
        ]
        materialized_issues = [
            issue
            for fragment in fragments
            for issue in validate_materialized_record(fragment, source_document=source_document)
        ]
        if materialized_issues:
            formatted = "\n".join(
                f"[{issue.code}] {issue.message}" for issue in materialized_issues
            )
            raise HarvestContractError(
                f"Materialized provenance self-check failed:\n{formatted}",
                issues=materialized_issues,
            )

        # Source identity is deterministic and never delegated to the model.
        source_ref = HarvestSourceRef(
            pipeline="exegate",
            source_path=envelope.source_path,
            source_sha256=envelope.source_sha256,
            source_title=source_document.get("song_title"),
            bundle_id=bundle_id,
        )
        manifest = export_harvest(
            out_root=out_root,
            run_id=actual_run_id,
            source=source_ref,
            result=result,
            fragments=fragments,
            write_library=write_library,
        )
        return HarvestExecution(
            source_path=Path(envelope.source_path),
            run_id=actual_run_id,
            fragments=tuple(fragments),
            manifest=manifest,
        )
