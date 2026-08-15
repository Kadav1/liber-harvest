import json
from pathlib import Path
from liber_harvest.adapters.exegate.loader import ExegateAdapter, stable_source_path
from liber_harvest.adapters.exegate.parser import parse_exegate_markdown

def test_json_adapter_is_standalone(tmp_path):
    repo=tmp_path/'repo'; (repo/'pyproject.toml').parent.mkdir(parents=True,exist_ok=True); (repo/'pyproject.toml').write_text('[project]\nname="legacy"\n')
    src=repo/'data'/'song.json'; src.parent.mkdir(); src.write_text(json.dumps({'song_title':'X','scene_hooks':[{'hook_text_raw':'A hook.'}]}))
    loaded=ExegateAdapter().load(src)
    assert loaded.envelope.source_path=='data/song.json'
    assert loaded.document['song_title']=='X'

def test_markdown_parser_recovers_structured_fields(tmp_path):
    p=tmp_path/'x.md'; p.write_text('Song Title: Test\nAnalysis Mode: Exegate\n\n## VII. Narrative Potential\n1. A field might be consecrated.\n\n## VIII. Seed Line Distillation\n1. The snow remembers.\nUse: epitaph\n')
    run=parse_exegate_markdown(p)
    assert run.song_title=='Test' and run.scene_hooks and run.seed_lines
    assert run.seed_lines[0].use=='epitaph'
