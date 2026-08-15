"""Atomic JSON and JSONL storage primitives."""
from __future__ import annotations
import json, os
from pathlib import Path
from typing import Iterable
from pydantic import BaseModel

def atomic_write(path:Path,data:bytes)->None:
    path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_name(path.name+'.tmp'); tmp.write_bytes(data); os.replace(tmp,path)

def json_bytes(value:object,*,indent:int|None=2)->bytes:
    return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=indent)+'\n').encode('utf-8')

def jsonl_bytes(records:Iterable[BaseModel])->bytes:
    lines=[json.dumps(r.model_dump(mode='json'),ensure_ascii=False,sort_keys=True,separators=(',',':')) for r in records]
    return (("\n".join(lines)+"\n") if lines else '').encode('utf-8')

def upsert_fragment_library(path:Path,records:Iterable[BaseModel])->None:
    existing={}
    if path.exists():
        for lineno,line in enumerate(path.read_text(encoding='utf-8').splitlines(),1):
            if not line.strip(): continue
            obj=json.loads(line)
            if 'fragment_id' not in obj: raise ValueError(f'{path}:{lineno}: missing fragment_id')
            existing[obj['fragment_id']]=obj
    for record in records: existing[record.fragment_id]=record.model_dump(mode='json')
    data=(("\n".join(json.dumps(existing[k],ensure_ascii=False,sort_keys=True,separators=(',',':')) for k in sorted(existing))+"\n") if existing else '').encode('utf-8')
    atomic_write(path,data)
