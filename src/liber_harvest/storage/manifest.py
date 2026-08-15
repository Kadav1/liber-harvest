"""Manifest helpers."""
from __future__ import annotations
import hashlib
from datetime import datetime, timezone
from ..constants import CONTRACT_VERSION, FRAGMENT_SCHEMA_VERSION, MANIFEST_VERSION
from ..models import HarvestManifest, HarvestSourceRef, ManifestCounts, JsonArtifactInfo, JsonlArtifactInfo

def sha256_bytes(data:bytes)->str: return hashlib.sha256(data).hexdigest()

def build_manifest(*,run_id:str,source:HarvestSourceRef,fragment_bytes:bytes,fragment_path:str,fragment_count:int,
                   run_bytes:bytes,run_path:str,coverage_count:int,discarded_count:int,warnings:list[str],review_required:int)->HarvestManifest:
    return HarvestManifest(manifest_version=MANIFEST_VERSION,run_id=run_id,contract_version=CONTRACT_VERSION,
        fragment_schema_version=FRAGMENT_SCHEMA_VERSION,source=source,
        counts=ManifestCounts(fragments=fragment_count,coverage_entries=coverage_count,discarded=discarded_count,
                              warnings=len(warnings),review_required=review_required),
        artifacts={'fragments_jsonl':JsonlArtifactInfo(path=fragment_path,sha256=sha256_bytes(fragment_bytes),records=fragment_count),
                   'run_json':JsonArtifactInfo(path=run_path,sha256=sha256_bytes(run_bytes))},
        warnings=warnings,created_at=datetime.now(timezone.utc))
