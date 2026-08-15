from __future__ import annotations
import copy, hashlib
from pathlib import Path
import pytest

SHA='0'*64

def draft_payload(*,source_path='source.json',source_sha=SHA,pointer='/scene_hooks/0/hook_text_raw',excerpt='might be consecrated',concept_key='winter_snow_funerary_memory'):
    return {
      'concept_key':concept_key,'type':'custom','title':'Snow as Funerary Memory','claim':{'modality':'proposed'},
      'content':{'source_meaning':'A hook proposes a burial field shaped by snow.',
                 'normalized_lore':'One proposed funerary custom allows snow to participate in remembrance.','details':[]},
      'domains':['burial','environment'],'tags':['snow','funerary_memory'],'legacy_bindings':[],
      'derivation':{'primary_mode':'generalized','operations':['decomposed','generalized'],'fidelity':'high','inference_note':None},
      'provenance':[{'pipeline':'exegate','source_path':source_path,'source_sha256':source_sha,'source_title':'Example','bundle_id':None,'source_item_id':None,
                     'circle':'narrative_potential','evidence_layer':'generated_hook','source_modality':'proposed','json_pointer':pointer,'role':'primary','excerpt':excerpt}],
      'relation_hints':[],'review':{'required':False,'reasons':[]}}

def sha256_file(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

@pytest.fixture
def payload_factory(): return draft_payload
