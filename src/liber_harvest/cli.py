"""Command-line interface for the standalone Liber Harvest tool."""
from __future__ import annotations
import json, os
from pathlib import Path
from typing import Optional
import typer
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table
from .adapters.exegate.loader import discover_sources, ExegateAdapter
from .models import LoreFragmentRecord
from .pipeline import HarvestContractError, LiberHarvester
from .providers.lmstudio import LMStudioProvider
from .providers.static import StaticProvider
from .validation import validate_materialized_record

app=typer.Typer(help='Liber Harvest: provenance-preserving historical lore recovery',rich_markup_mode=None)
harvest_app=typer.Typer(help='Run frozen harvest pipelines',rich_markup_mode=None); app.add_typer(harvest_app,name='harvest')
console=Console()

def _provider(*,model:Optional[str],lm_studio_url:Optional[str],response_file:Optional[Path],temperature:float,max_output_tokens:int,timeout:float):
    if response_file: return StaticProvider.from_file(response_file)
    if not model: raise typer.BadParameter('--model is required unless --response-file is supplied')
    url=lm_studio_url or os.getenv('LIBER_HARVEST_LM_STUDIO_URL','http://127.0.0.1:1234')
    return LMStudioProvider(base_url=url,model=model,temperature=temperature,max_output_tokens=max_output_tokens,timeout=timeout)

def _print(execution):
    t=Table(title=f'Liber Harvest {execution.run_id}'); t.add_column('Metric');t.add_column('Value')
    t.add_row('Fragments',str(len(execution.fragments)));t.add_row('Review required',str(sum(x.review.required for x in execution.fragments)))
    t.add_row('Manifest',str(execution.manifest.artifacts.run_json.path));console.print(t)

@harvest_app.command('exegate')
def harvest_exegate(source:Optional[Path]=typer.Argument(None),all_sources:bool=typer.Option(False,'--all'),
    source_root:Path=typer.Option(Path('data/parsed'),'--source-root'),model:Optional[str]=typer.Option(None,'--model'),
    lm_studio_url:Optional[str]=typer.Option(None,'--lm-studio-url'),response_file:Optional[Path]=typer.Option(None,'--response-file'),
    temperature:float=typer.Option(0.1,'--temperature'),max_output_tokens:int=typer.Option(32768,'--max-output-tokens'),
    timeout:float=typer.Option(300.0,'--timeout'),out:Path=typer.Option(Path('harvest'),'--out'),
    no_library:bool=typer.Option(False,'--no-library'),run_id:Optional[str]=typer.Option(None,'--run-id')):
    if all_sources and source is not None: raise typer.BadParameter('Provide SOURCE or --all, not both')
    if not all_sources and source is None: raise typer.BadParameter('SOURCE is required unless --all is used')
    if all_sources and (response_file or run_id): raise typer.BadParameter('--response-file/--run-id are single-source only')
    provider=_provider(model=model,lm_studio_url=lm_studio_url,response_file=response_file,temperature=temperature,max_output_tokens=max_output_tokens,timeout=timeout)
    harvester=LiberHarvester(provider); sources=discover_sources(source_root) if all_sources else [source]
    if not sources: console.print('[yellow]No Exegate sources found[/yellow]'); raise typer.Exit(2)
    failures=0
    for item in sources:
        try: _print(harvester.run(item,out_root=out,run_id=run_id if len(sources)==1 else None,write_library=not no_library))
        except (HarvestContractError,ValidationError,ValueError,OSError) as exc:
            failures+=1; console.print(f'[bold red]✗[/bold red] {item}: {exc}')
            if len(sources)==1: raise typer.Exit(3)
    if failures: raise typer.Exit(3)

@app.command('validate')
def validate(path:Path=typer.Argument(...),provenance:bool=typer.Option(False,'--provenance')):
    failures=0; records=0; adapter=ExegateAdapter(); cache={}
    for lineno,line in enumerate(path.read_text(encoding='utf-8').splitlines(),1):
        if not line.strip(): failures+=1; console.print(f'[red]L{lineno}: blank JSONL line[/red]'); continue
        records+=1
        try:
            record=LoreFragmentRecord.model_validate_json(line)
            if provenance:
                sp=record.provenance[0].source_path
                if sp not in cache:
                    loaded=adapter.load(Path(sp)); cache[sp]=None if loaded.envelope.source_sha256!=record.provenance[0].source_sha256 else loaded.document
                    if cache[sp] is None: failures+=1; console.print(f'[red]L{lineno}: PROVENANCE STALE - source SHA changed[/red]')
                if cache.get(sp) is not None:
                    for issue in validate_materialized_record(record,source_document=cache[sp]): failures+=1; console.print(f'[red]L{lineno}: {issue.code}: {issue.message}[/red]')
        except (ValidationError,OSError,ValueError) as exc: failures+=1; console.print(f'[red]L{lineno}: {exc}[/red]')
    if failures: console.print(f'[bold red]Validation failed: {failures} issue(s)[/bold red]'); raise typer.Exit(3)
    console.print(f'[bold green]✓[/bold green] {records} Lore Fragment record(s) valid')

@app.command('inspect')
def inspect_fragment(fragment_id:str,library:Path=typer.Option(Path('harvest/library/fragments.jsonl'),'--library')):
    for line in library.read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        obj=json.loads(line)
        if obj.get('fragment_id')==fragment_id: console.print_json(json.dumps(obj,ensure_ascii=False)); return
    console.print(f'[yellow]Fragment not found:[/yellow] {fragment_id}'); raise typer.Exit(2)

@app.command('version')
def version():
    from . import __version__; console.print(f'Liber Harvest {__version__}')
