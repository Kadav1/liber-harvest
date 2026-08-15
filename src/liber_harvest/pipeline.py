"""High-level Liber Harvest orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from .providers.base import ExtractionProvider
from .constants import EXTRACTOR_VERSION
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
    def __init__(self, provider: ExtractionProvider, *, adapter: SourceAdapter | None = None, max_repairs: int = 1):
        self.provider = provider
        self.adapter = adapter or ExegateAdapter()
        self.max_repairs = max_repairs

    @staticmethod
    def make_run_id(source_sha256: str) -> str:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        return f"LHR-{stamp}-{source_sha256[:8].upper()}"

    def _extract_and_validate(self, envelope) -> ExegateHarvestResult:
        candidate = self.provider.extract(envelope)
        for attempt in range(self.max_repairs + 1):
            try:
                return ExegateHarvestResult.model_validate(candidate)
            except ValidationError as exc:
                if attempt >= self.max_repairs:
                    raise HarvestContractError(f"Extractor output failed v0.1.2 schema validation: {exc}") from exc
                candidate = self.provider.repair(candidate, str(exc), envelope)
        raise AssertionError("unreachable")

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
        if issues and self.max_repairs > 0:
            formatted = "\n".join(f"[{issue.code}] {issue.message}" for issue in issues)
            repaired = self.provider.repair(
                result.model_dump(mode="json"),
                "Deterministic contract validation failed:\n" + formatted,
                envelope,
            )
            try:
                result = ExegateHarvestResult.model_validate(repaired)
            except ValidationError as exc:
                raise HarvestContractError(
                    f"Repaired extractor output failed v0.1.2 schema validation: {exc}"
                ) from exc
            issues = validate_result_against_source(
                result,
                source_path=envelope.source_path,
                source_sha256=envelope.source_sha256,
                source_document=source_document,
            )
        if issues:
            formatted = "\n".join(f"[{issue.code}] {issue.message}" for issue in issues)
            raise HarvestContractError(
                f"Harvest result failed deterministic validation:\n{formatted}", issues=issues
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
