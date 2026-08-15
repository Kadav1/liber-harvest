from liber_harvest.models import ExegateHarvestResult
from liber_harvest.validation import validate_result_against_source, validate_materialized_record
from liber_harvest.materializer import materialize_fragment
from liber_harvest.models import LoreFragmentDraft

def make_result(payload_factory, normalized=None):
    p=payload_factory(source_path='source.json')
    if normalized is not None: p['content']['normalized_lore']=normalized
    p['provenance'][0]['excerpt']='might be consecrated'
    return {'contract_version':'exegate-harvest/0.1.2','source':{'pipeline':'exegate','source_path':'source.json','source_sha256':'0'*64,'source_title':'Example','bundle_id':None},
            'fragments':[p],'coverage':[{'json_pointer':'/scene_hooks','disposition':'extracted','evidence_layer':'generated_hook','source_modality':'proposed','concept_keys':[p['concept_key']]}],
            'discarded':[],'warnings':[]}

def test_pipeline_wrapper_leak(payload_factory):
    result=ExegateHarvestResult.model_validate(make_result(payload_factory,'Lore Architect could create this rite.'))
    issues=validate_result_against_source(result,source_path='source.json',source_sha256='0'*64,source_document={'scene_hooks':[{'hook_text_raw':'might be consecrated'}]})
    assert any(x.code=='pipeline_wrapper_leak' for x in issues)

def test_modality_wording_must_be_visible(payload_factory):
    result=ExegateHarvestResult.model_validate(make_result(payload_factory,'A community reserves a field for the dead.'))
    issues=validate_result_against_source(result,source_path='source.json',source_sha256='0'*64,source_document={'scene_hooks':[{'hook_text_raw':'might be consecrated'}]})
    assert any(x.code=='modality_wording_unsafe' for x in issues)

def test_stale_source_detected(payload_factory):
    p=payload_factory(); p['provenance'][0]['excerpt']='might be consecrated'
    record=materialize_fragment(LoreFragmentDraft.model_validate(p),source_document={'scene_hooks':[{'hook_text_raw':'A field might be consecrated.'}]},run_id='R')
    issues=validate_materialized_record(record,source_document={'scene_hooks':[{'hook_text_raw':'A field was abandoned.'}]})
    assert any(x.code=='provenance_stale' for x in issues)
