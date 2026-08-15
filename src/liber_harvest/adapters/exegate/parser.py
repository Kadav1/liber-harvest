\
"""Tolerant parser for historical Infernal Exegate Markdown."""
from __future__ import annotations
import re
from pathlib import Path
from .models import ExegateRun, RitualItem, SceneHookItem, SeedLineItem, SymbolItem, VectorItem

_SECTION_PATTERNS={
 "prima_materia":r"^i\.?\s+prima\s+materia",
 "vectors_of_corruption":r"^ii\.?\s+vectors?\s+of\s+corruption",
 "symbol_harvest":r"^iii\.?\s+symbol\s+harvest",
 "psychological_pathology":r"^iv\.?\s+psychological\s+pathology",
 "ritual_extraction":r"^v\.?\s+ritual\s+extraction",
 "atmospherics_texture":r"^vi\.?\s+atmospherics",
 "narrative_potential":r"^vii\.?\s+narrative\s+potential",
 "seed_line_distillation":r"^viii\.?\s+seed\s+line",
 "metadata_assessment":r"^metadata\s+(&|and)\s+assessment",
 "naming_ids":r"^naming\s+(&|and)?\s*ids?",
}

def _clean(line:str)->str:
    value=line.strip(); value=re.sub(r"^#{1,6}\s*","",value); value=value.replace("**","")
    value=re.sub(r"^[•*-]\s*","",value); return value.strip()

def _heading(line:str)->str|None:
    n=_clean(line).lower()
    for key,pat in _SECTION_PATTERNS.items():
        if re.search(pat,n): return key
    return None

def _sections(lines:list[str])->dict[str,list[str]]:
    out={"preamble":[]}; current="preamble"
    for line in lines:
        key=_heading(line)
        if key: current=key; out.setdefault(key,[]).append(line)
        else: out.setdefault(current,[]).append(line)
    return out

def _body(lines:list[str]|None)->str|None:
    if not lines: return None
    text="\n".join(lines[1:]).strip(); return text or None

def _field(lines:list[str], label:str)->str|None:
    pat=re.compile(rf"^{re.escape(label)}\s*:\s*(.+)$",re.I)
    for line in lines:
        m=pat.match(_clean(line))
        if m: return m.group(1).strip()
    return None

def _int(value:str|None)->int|None:
    if value is None:return None
    m=re.search(r"-?\d+",str(value)); return int(m.group()) if m else None

def parse_symbols(lines:list[str])->list[SymbolItem]:
    items=[]; cur=None
    for line in lines:
        c=_clean(line); m=re.match(r"^symbol\s*:\s*(.+)",c,re.I)
        if m:
            if cur: items.append(cur)
            cur=SymbolItem(name=m.group(1).strip()); continue
        if not cur: continue
        low=c.lower()
        if low.startswith("literal:"): cur.literal=c.split(":",1)[1].strip()
        elif low.startswith("occult:"): cur.occult=c.split(":",1)[1].strip()
        elif low.startswith("psychological:"): cur.psychological=c.split(":",1)[1].strip()
        elif low.startswith("lv hook:"): cur.lv_hook=c.split(":",1)[1].strip()
        elif low.startswith("metadata:"):
            cur.metadata_raw=c.split(":",1)[1].strip()
            mm=re.search(r"intensity[=:]\s*(\d+)",cur.metadata_raw,re.I); cur.intensity=_int(mm.group(1)) if mm else None
            mm=re.search(r"texture[=:]\s*([^|]+)",cur.metadata_raw,re.I); cur.texture=mm.group(1).strip() if mm else None
            mm=re.search(r"phase[=:]\s*([IVX0-9N]+)",cur.metadata_raw,re.I); cur.phase=mm.group(1).strip() if mm else None
    if cur: items.append(cur)
    return items

def parse_vectors(lines:list[str])->list[VectorItem]:
    items=[]; cur=None
    for line in lines:
        c=_clean(line)
        m=re.match(r"^(?:vector\s*:\s*|\d+[.)]\s*)([^:]{2,120})(?::\s*(.*))?$",c,re.I)
        if m and not c.lower().startswith(("intensity:","texture:","phase:")):
            if cur: items.append(cur)
            cur=VectorItem(name=m.group(1).strip(),description=(m.group(2) or "").strip() or None); continue
        if cur and c and not re.match(r"^[A-Z][A-Za-z ]+\s*:",c):
            cur.description=((cur.description+" ") if cur.description else "")+c
    if cur: items.append(cur)
    return items

def parse_rituals(lines:list[str])->list[RitualItem]:
    items=[]; cur=None
    for line in lines:
        c=_clean(line); name=None; typ=None
        m=re.match(r"^(.+?)\s*\(Type:\s*(.+?)\)\s*$",c,re.I)
        if m: name=m.group(1).strip(); typ=m.group(2).strip()
        else:
            m=re.match(r"^(?:ritual\s*:\s*|\d+[.)]\s*)(.+)$",c,re.I)
            if m and not c.lower().startswith(("description:","placement:","alexius resonance:","intensity:","phase:","texture:")):
                name=m.group(1).strip()
        if name:
            if cur: items.append(cur)
            cur=RitualItem(name=name,type=typ); continue
        if not cur: continue
        low=c.lower()
        if low.startswith("type:"): cur.type=c.split(":",1)[1].strip()
        elif low.startswith("description:"): cur.description=c.split(":",1)[1].strip()
        elif low.startswith("placement:"): cur.placement=c.split(":",1)[1].strip()
        elif low.startswith("alexius resonance:"): cur.alexius_resonance=c.split(":",1)[1].strip()
        elif low.startswith("intensity:"): cur.intensity=_int(c.split(":",1)[1])
        elif low.startswith("phase:"): cur.phase=c.split(":",1)[1].strip()
        elif low.startswith("texture:"): cur.texture=c.split(":",1)[1].strip()
        elif c: cur.description=((cur.description+"\n") if cur.description else "")+c
    if cur: items.append(cur)
    return items

def parse_seed_lines(lines:list[str])->list[SeedLineItem]:
    items=[]; cur=None
    for line in lines:
        c=_clean(line)
        m=re.match(r"^(?:seed\s*line\s*:\s*|\d+[.)]\s*)([\"“']?.+)",c,re.I)
        if m and not c.lower().startswith(("intensity:","texture:","phase:","voice:","use:","lexicon:")):
            if cur: items.append(cur)
            text=m.group(1).strip().strip('"“”'); cur=SeedLineItem(seed_line=text); continue
        if not cur: continue
        low=c.lower()
        if low.startswith("intensity:"): cur.intensity=_int(c.split(":",1)[1])
        elif low.startswith("texture:"): cur.texture=c.split(":",1)[1].strip()
        elif low.startswith("phase:"): cur.phase=c.split(":",1)[1].strip()
        elif low.startswith("voice:"): cur.voice=c.split(":",1)[1].strip()
        elif low.startswith("use:"): cur.use=c.split(":",1)[1].strip()
        elif low.startswith("lexicon:"): cur.lexicon=[x.strip() for x in c.split(":",1)[1].split(",") if x.strip()]
    if cur: items.append(cur)
    return items

def parse_scene_hooks(lines:list[str])->list[SceneHookItem]:
    items=[]; cur=None
    for line in lines:
        c=_clean(line)
        m=re.match(r"^(?:scene\s*hook\s*:\s*|hook\s*:\s*|\d+[.)]\s*)(.+)$",c,re.I)
        heading=re.match(r"^#{0,6}\s*([^:]{3,100})$",line.strip()) if line.strip().startswith("#") else None
        if m:
            if cur: items.append(cur)
            cur=SceneHookItem(hook_text_raw=m.group(1).strip()); continue
        if heading and cur is None: cur=SceneHookItem(hook_text_raw="",hook_title=_clean(line)); continue
        if not cur:
            if c: cur=SceneHookItem(hook_text_raw=c)
            continue
        low=c.lower()
        if low.startswith("title:"): cur.hook_title=c.split(":",1)[1].strip()
        elif low.startswith("type:"): cur.hook_type=c.split(":",1)[1].strip()
        elif low.startswith("phase:"): cur.phase=c.split(":",1)[1].strip()
        elif low.startswith("texture:"): cur.texture=c.split(":",1)[1].strip()
        elif c: cur.hook_text_raw=(cur.hook_text_raw+"\n"+c).strip()
    if cur and cur.hook_text_raw: items.append(cur)
    return items

def parse_exegate_markdown(path:Path)->ExegateRun:
    lines=path.read_text(encoding="utf-8").splitlines(); sec=_sections(lines)
    return ExegateRun(
        song_title=_field(sec.get("preamble",[]),"Song Title"), analysis_mode=_field(sec.get("preamble",[]),"Analysis Mode"),
        prima_materia_raw=_body(sec.get("prima_materia")), vectors_raw=_body(sec.get("vectors_of_corruption")),
        vectors=parse_vectors(sec.get("vectors_of_corruption",[])), symbols=parse_symbols(sec.get("symbol_harvest",[])),
        psych_pathology_raw=_body(sec.get("psychological_pathology")), rituals=parse_rituals(sec.get("ritual_extraction",[])),
        atmospherics_raw=_body(sec.get("atmospherics_texture")), scene_hooks=parse_scene_hooks(sec.get("narrative_potential",[])),
        seed_lines=parse_seed_lines(sec.get("seed_line_distillation",[])), metadata_raw=_body(sec.get("metadata_assessment")),
        naming_ids_raw=_body(sec.get("naming_ids")))
