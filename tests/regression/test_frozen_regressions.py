from __future__ import annotations
from pathlib import Path
from liber_harvest.adapters.exegate.loader import ExegateAdapter
from liber_harvest.pipeline import LiberHarvester
from liber_harvest.providers.static import StaticProvider

ROOT=Path(__file__).resolve().parents[2]

def run_case(tmp_path,case_id,*,pointer,excerpt,concept_key,modality,evidence_layer,normalized,typ='belief',circle='narrative_potential'):
    source=ROOT/'tests'/'fixtures'/case_id/'source.json'; loaded=ExegateAdapter().load(source)
    result={'contract_version':'exegate-harvest/0.1.2','source':{'pipeline':'exegate','source_path':loaded.envelope.source_path,'source_sha256':loaded.envelope.source_sha256,'source_title':loaded.document.get('song_title'),'bundle_id':loaded.bundle_id},
      'fragments':[{'concept_key':concept_key,'type':typ,'title':concept_key.replace('_',' ').title(),'claim':{'modality':modality},
        'content':{'source_meaning':'Historical source evidence recovered for regression.','normalized_lore':normalized,'details':[]},
        'domains':['religion'] if typ in {'belief','doctrine','ritual'} else ['burial'],'tags':['regression'], 'legacy_bindings':[],
        'derivation':{'primary_mode':'generalized','operations':['decomposed','generalized'],'fidelity':'high','inference_note':None},
        'provenance':[{'pipeline':'exegate','source_path':loaded.envelope.source_path,'source_sha256':loaded.envelope.source_sha256,'source_title':loaded.document.get('song_title'),'bundle_id':loaded.bundle_id,'source_item_id':None,'circle':circle,'evidence_layer':evidence_layer,'source_modality':modality,'json_pointer':pointer,'role':'primary','excerpt':excerpt}],
        'relation_hints':[],'review':{'required':False,'reasons':[]}}],
      'coverage':[], 'discarded':[], 'warnings':[]}
    # every non-empty primary source field must receive top-level coverage
    from liber_harvest.constants import PRIMARY_EXEGATE_FIELDS, FIELD_TO_CIRCLE
    for field in PRIMARY_EXEGATE_FIELDS:
        value=loaded.document.get(field)
        if value not in (None,'',[],{}):
            result['coverage'].append({'json_pointer':f'/{field}','disposition':'extracted' if field==pointer.split('/')[1] else 'metadata_only',
              'evidence_layer':evidence_layer if field==pointer.split('/')[1] else None,'source_modality':modality if field==pointer.split('/')[1] else None,
              'concept_keys':[concept_key] if field==pointer.split('/')[1] else []})
    return LiberHarvester(StaticProvider(result),max_repairs=0).run(source,out_root=tmp_path,run_id=case_id)

def test_T02_structured_source(tmp_path):
    e=run_case(tmp_path,'T02',pointer='/rituals/0/description',excerpt='might unknowingly ingest minute doses',concept_key='communal_minute_dose_exposure',modality='proposed',evidence_layer='lv_application',normalized='One proposed ritual practice may expose members to minute doses during communal observance.',typ='ritual',circle='ritual_extraction')
    assert e.fragments[0].provenance[0].evidence_layer.value=='lv_application'

def test_T03_proposal_modality(tmp_path):
    e=run_case(tmp_path,'T03',pointer='/scene_hooks/0/hook_text_raw',excerpt='might be consecrated for failed initiates',concept_key='remote_failed_initiate_burial',modality='proposed',evidence_layer='generated_hook',normalized='One proposed funerary custom might reserve a remote field for failed initiates.',typ='custom')
    assert e.fragments[0].claim.modality.value=='proposed'
    assert 'Lore Architect' not in e.fragments[0].content.normalized_lore

def test_T04_evidence_layer(tmp_path):
    e=run_case(tmp_path,'T04',pointer='/vectors_raw',excerpt='interprets the growth as an inversion of grace',concept_key='sacred_pathology_inversion',modality='interpretive',evidence_layer='exegate_interpretation',normalized='One interpretive reading treats bodily deterioration as an inversion of grace.',typ='doctrine',circle='vectors_of_corruption')
    assert e.fragments[0].provenance[0].evidence_layer.value=='exegate_interpretation'

def test_T10_contradiction_interpretation(tmp_path):
    e=run_case(tmp_path,'T10',pointer='/scene_hooks/0/hook_text_raw',excerpt='might record the crimson rain as a plague omen',concept_key='crimson_rain_plague_omen',modality='proposed',evidence_layer='generated_hook',normalized='One proposed external interpretation might treat crimson rain as a plague omen.',typ='belief')
    assert e.fragments[0].claim.modality.value=='proposed'
