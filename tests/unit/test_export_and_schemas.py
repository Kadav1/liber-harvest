import hashlib, json
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from liber_harvest.exporter import export_harvest
from liber_harvest.materializer import materialize_fragment
from liber_harvest.models import ExegateHarvestResult, HarvestSourceRef, LoreFragmentDraft

def test_export_hashes_and_jsonl(tmp_path,payload_factory):
    p=payload_factory(source_path='source.json');p['provenance'][0]['excerpt']='might be consecrated'
    source_doc={'scene_hooks':[{'hook_text_raw':'A field might be consecrated.'}]}
    record=materialize_fragment(LoreFragmentDraft.model_validate(p),source_document=source_doc,run_id='R')
    result=ExegateHarvestResult.model_validate({'contract_version':'exegate-harvest/0.1.2','source':{'pipeline':'exegate','source_path':'source.json','source_sha256':'0'*64,'source_title':'Example','bundle_id':None},'fragments':[p],'coverage':[{'json_pointer':'/scene_hooks','disposition':'extracted','evidence_layer':'generated_hook','source_modality':'proposed','concept_keys':[p['concept_key']]}],'discarded':[],'warnings':[]})
    manifest=export_harvest(out_root=tmp_path,run_id='R',source=HarvestSourceRef(pipeline='exegate',source_path='source.json',source_sha256='0'*64,source_title='Example',bundle_id=None),result=result,fragments=[record])
    fp=Path(manifest.artifacts.fragments_jsonl.path); assert hashlib.sha256(fp.read_bytes()).hexdigest()==manifest.artifacts.fragments_jsonl.sha256
    assert json.loads(fp.read_text().strip())['fragment_id']==record.fragment_id

def test_machine_schemas_self_validate():
    schema_dir=Path(__file__).resolve().parents[2]/'schemas'/'v0.1.2'
    for path in schema_dir.glob('*.schema.json'): Draft202012Validator.check_schema(json.loads(path.read_text()))
