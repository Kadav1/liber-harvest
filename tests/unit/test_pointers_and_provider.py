import pytest
from liber_harvest.pointers import JsonPointerError, resolve_json_pointer
from liber_harvest.providers.lmstudio import normalize_lmstudio_base
from liber_harvest.jsonutil import parse_json_object

def test_pointer_escape(): assert resolve_json_pointer({'a/b':{'~key':'ok'}},'/a~1b/~0key')=='ok'
def test_bad_pointer_escape():
    with pytest.raises(JsonPointerError): resolve_json_pointer({'x':1},'/bad~pointer')
def test_array_leading_zero():
    with pytest.raises(JsonPointerError): resolve_json_pointer(['a','b'],'/01')
def test_lmstudio_normalization():
    assert normalize_lmstudio_base('http://host:1234/v1')=='http://host:1234'
    assert normalize_lmstudio_base('http://host:1234/')=='http://host:1234'
def test_model_json_plain_and_fenced():
    assert parse_json_object('{"a":1}')=={'a':1}
    assert parse_json_object('```json\n{"a":1}\n```')=={'a':1}
