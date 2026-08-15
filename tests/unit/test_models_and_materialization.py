from copy import deepcopy
import pytest
from pydantic import ValidationError
from liber_harvest.models import LoreFragmentDraft
from liber_harvest.materializer import materialize_fragment
from liber_harvest.provenance import materialize_provenance_anchor


def test_materialization_is_deterministic(payload_factory):
    p=payload_factory(); p['provenance'][0]['excerpt']='might be consecrated'
    source={'scene_hooks':[{'hook_text_raw':'A field might be consecrated for the dead.'}]}
    draft=LoreFragmentDraft.model_validate(p)
    a=materialize_fragment(draft,source_document=source,run_id='R1'); b=materialize_fragment(draft,source_document=source,run_id='R2')
    assert a.fragment_id==b.fragment_id and a.fragment_id.startswith('LFR-CUS-')
    assert a.provenance[0].precision.value=='span'

def test_ambiguous_claim_requires_review(payload_factory):
    p=payload_factory(); p['claim']['modality']='ambiguous'
    with pytest.raises(ValidationError): LoreFragmentDraft.model_validate(p)

def test_asserted_claim_requires_asserted_anchor(payload_factory):
    p=payload_factory(); p['claim']['modality']='asserted'
    with pytest.raises(ValidationError): LoreFragmentDraft.model_validate(p)

def test_direct_is_exclusive(payload_factory):
    p=payload_factory(); p['derivation']={'primary_mode':'direct','operations':['direct','generalized'],'fidelity':'high','inference_note':None}
    with pytest.raises(ValidationError): LoreFragmentDraft.model_validate(p)

def test_unresolved_excerpt_flags_review(payload_factory):
    draft=LoreFragmentDraft.model_validate(payload_factory())
    record=materialize_fragment(draft,source_document={'scene_hooks':[{'hook_text_raw':'different text'}]},run_id='R')
    assert record.review.required and 'provenance_excerpt_unresolved' in [x.value for x in record.review.reasons]

def test_ambiguous_excerpt_does_not_guess(payload_factory):
    draft=LoreFragmentDraft.model_validate(payload_factory(excerpt='ritual dust',pointer='/vectors_raw'))
    result=materialize_provenance_anchor(draft.provenance[0],{'vectors_raw':'ritual dust / ritual dust'})
    assert result.anchor.precision.value=='field'
    assert 'provenance_span_ambiguous' in [x.value for x in result.review_reasons]
