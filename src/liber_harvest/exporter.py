"""Export a validated harvest into the frozen file-first layout."""
from __future__ import annotations
import re
from pathlib import Path
from .constants import CONTRACT_VERSION
from .models import ExegateHarvestResult, HarvestSourceRef, LoreFragmentRecord
from .storage.jsonl import atomic_write, json_bytes, jsonl_bytes, upsert_fragment_library
from .storage.manifest import build_manifest

def _slug(value:str)->str:
    value=re.sub(r'[^a-zA-Z0-9._-]+','-',value).strip('-._').lower(); return value or 'source'
def source_key(source_path:str,sha:str)->str: return f"{_slug(Path(source_path).stem)}-{sha[:12]}"

def export_harvest(*,out_root:Path,run_id:str,source:HarvestSourceRef,result:ExegateHarvestResult,
                   fragments:list[LoreFragmentRecord],write_library:bool=True):
    key=source_key(source.source_path,source.source_sha256); source_dir=out_root/'exegate'/'sources'/key; runs=out_root/'exegate'/'runs'
    fragment_bytes=jsonl_bytes(fragments); source_fragments=source_dir/'fragments.jsonl'; atomic_write(source_fragments,fragment_bytes)
    run_payload={'contract_version':CONTRACT_VERSION,'run_id':run_id,'source':source.model_dump(mode='json'),
                 'coverage':[x.model_dump(mode='json') for x in result.coverage],
                 'discarded':[x.model_dump(mode='json') for x in result.discarded],'warnings':result.warnings,
                 'fragments':[x.model_dump(mode='json') for x in fragments]}
    run_bytes=json_bytes(run_payload); run_path=runs/f'{run_id}.json'; atomic_write(run_path,run_bytes)
    if write_library:
        lib=out_root/'library'; upsert_fragment_library(lib/'fragments.jsonl',fragments)
        if not (lib/'relations.jsonl').exists(): atomic_write(lib/'relations.jsonl',b'')
    manifest=build_manifest(run_id=run_id,source=source,fragment_bytes=fragment_bytes,fragment_path=str(source_fragments),
        fragment_count=len(fragments),run_bytes=run_bytes,run_path=str(run_path),coverage_count=len(result.coverage),
        discarded_count=len(result.discarded),warnings=result.warnings,review_required=sum(1 for x in fragments if x.review.required))
    atomic_write(source_dir/'harvest_manifest.json',json_bytes(manifest.model_dump(mode='json')))
    return manifest
