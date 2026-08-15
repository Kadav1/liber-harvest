"""Load authoritative historical Exegate sources without importing LV-Forge."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any
from ...constants import CONTRACT_VERSION
from ...models import HarvestInputEnvelope
from ..base import LoadedSource
from .models import ExegateRun
from .parser import parse_exegate_markdown

class SourceLoadError(ValueError): pass

def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def resolve_source_path(path:Path)->Path:
    actual=path.expanduser().resolve()
    if actual.is_dir():
        candidate=actual/'exegate_run.json'
        if not candidate.exists(): raise SourceLoadError(f"Directory does not contain exegate_run.json: {actual}")
        return candidate
    if not actual.exists(): raise FileNotFoundError(actual)
    return actual

def _project_root(actual:Path)->Path|None:
    for parent in (actual.parent,*actual.parents):
        if (parent/'.git').exists() or (parent/'pyproject.toml').exists(): return parent
    return None

def stable_source_path(actual:Path)->str:
    actual=actual.resolve(); root=_project_root(actual)
    return actual.relative_to(root).as_posix() if root and actual.is_relative_to(root) else actual.as_posix()

def _bundle_id(data:dict[str,Any])->str|None:
    for field in ('symbols','rituals','scene_hooks','seed_lines','vectors'):
        for item in data.get(field) or []:
            if isinstance(item,dict) and item.get('bundle_id'): return str(item['bundle_id'])
    return None

class ExegateAdapter:
    pipeline='exegate'
    def load(self,path:Path)->LoadedSource:
        actual=resolve_source_path(path); digest=sha256_file(actual)
        if actual.suffix.lower()=='.json':
            raw=json.loads(actual.read_text(encoding='utf-8'))
            if not isinstance(raw,dict): raise SourceLoadError('Exegate JSON source must contain one object')
            canonical=ExegateRun.model_validate(raw).model_dump(mode='json'); source_format='exegate_run_json'
        elif actual.suffix.lower() in {'.md','.markdown'}:
            canonical=parse_exegate_markdown(actual).model_dump(mode='json'); source_format='exegate_markdown'
        else: raise SourceLoadError(f'Unsupported Exegate source format: {actual.suffix}')
        envelope=HarvestInputEnvelope(contract_version=CONTRACT_VERSION,source_path=stable_source_path(actual),
            source_sha256=digest,source_format=source_format,source=canonical)
        return LoadedSource(actual,envelope,canonical,_bundle_id(canonical))

def discover_sources(root:Path)->list[Path]:
    return sorted(root.expanduser().glob('song_*.json')) if root.expanduser().exists() else []
