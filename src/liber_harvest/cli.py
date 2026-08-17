"""Command-line interface for the standalone Liber Harvest tool."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import httpx
import typer
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from .adapters.exegate.loader import ExegateAdapter, discover_sources
from .models import LoreFragmentRecord
from .pipeline import HarvestContractError, LiberHarvester
from .providers.lmstudio import LMStudioProvider, ReasoningMode
from .providers.static import StaticProvider
from .validation import validate_materialized_record

app = typer.Typer(help="Liber Harvest: provenance-preserving historical lore recovery", rich_markup_mode=None)
harvest_app = typer.Typer(help="Run frozen harvest pipelines", rich_markup_mode=None)
app.add_typer(harvest_app, name="harvest")
console = Console()

DEFAULT_LM_STUDIO_URL = "http://127.0.0.1:1234"
DEFAULT_MODEL = "qwen/qwen3.6-35b-a3b"
DEFAULT_CONTEXT_LENGTH = 65536
DEFAULT_REASONING = ReasoningMode.OFF


def _provider(
    *,
    model: Optional[str],
    lm_studio_url: Optional[str],
    response_file: Optional[Path],
    temperature: float,
    max_output_tokens: int,
    context_length: int,
    reasoning: ReasoningMode,
    timeout: float,
):
    if response_file:
        return StaticProvider.from_file(response_file)
    resolved_model = model or os.getenv("LIBER_HARVEST_MODEL") or DEFAULT_MODEL
    url = lm_studio_url or os.getenv("LIBER_HARVEST_LM_STUDIO_URL", DEFAULT_LM_STUDIO_URL)
    return LMStudioProvider(
        base_url=url,
        model=resolved_model,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        context_length=context_length,
        reasoning=reasoning,
        timeout=timeout,
        api_token=os.getenv("LIBER_HARVEST_LM_STUDIO_TOKEN"),
    )


def _print(execution):
    table = Table(title=f"Liber Harvest {execution.run_id}")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Fragments", str(len(execution.fragments)))
    table.add_row("Review required", str(sum(x.review.required for x in execution.fragments)))
    table.add_row("Manifest", str(execution.manifest.artifacts.run_json.path))
    console.print(table)


@app.command("init")
def init_workspace(
    root: Path = typer.Option(Path("."), "--root", help="Repository/workspace root."),
):
    """Create the local, untracked runtime workspace expected by Liber Harvest."""
    root = root.expanduser().resolve()
    created = []
    for relative in (Path("data/parsed"), Path("data/bundles"), Path("harvest")):
        path = root / relative
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created.append(relative.as_posix())
    console.print("[bold green]✓[/bold green] Liber Harvest runtime workspace ready")
    console.print(f"Root: {root}")
    console.print("Inputs: data/parsed/song_*.json or data/bundles/<bundle-id>/exegate_run.json")
    console.print("Outputs: harvest/")
    if created:
        console.print("Created: " + ", ".join(created))


@app.command("doctor")
def doctor(
    model: Optional[str] = typer.Option(None, "--model", help="LM Studio model key or loaded instance id."),
    lm_studio_url: Optional[str] = typer.Option(None, "--lm-studio-url"),
    context_length: int = typer.Option(DEFAULT_CONTEXT_LENGTH, "--context-length", min=4096),
    reasoning: ReasoningMode = typer.Option(DEFAULT_REASONING, "--reasoning"),
    source: Optional[Path] = typer.Option(None, "--source", help="Optional Exegate JSON/bundle to parse-check."),
    out: Path = typer.Option(Path("harvest"), "--out"),
):
    """Check local workspace, LM Studio connectivity/model state, and optional source parsing."""
    failures = 0
    warnings = 0
    url = lm_studio_url or os.getenv("LIBER_HARVEST_LM_STUDIO_URL", DEFAULT_LM_STUDIO_URL)
    resolved_model = model or os.getenv("LIBER_HARVEST_MODEL") or DEFAULT_MODEL

    def ok(message: str):
        console.print(f"[green]✓[/green] {message}")

    def warn(message: str):
        nonlocal warnings
        warnings += 1
        console.print(f"[yellow]![/yellow] {message}")

    def fail(message: str):
        nonlocal failures
        failures += 1
        console.print(f"[red]✗[/red] {message}")

    if Path("data/parsed").exists() and Path("data/bundles").exists():
        ok("runtime input directories exist")
    else:
        warn("runtime input directories are missing; run `liber-harvest init`")

    try:
        out.expanduser().mkdir(parents=True, exist_ok=True)
        probe = out.expanduser() / ".liber-harvest-write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        ok(f"output directory is writable: {out}")
    except OSError as exc:
        fail(f"output directory is not writable: {exc}")

    provider = LMStudioProvider(
        base_url=url,
        model=resolved_model,
        context_length=context_length,
        reasoning=reasoning,
        timeout=30.0,
        api_token=os.getenv("LIBER_HARVEST_LM_STUDIO_TOKEN"),
    )
    try:
        status = provider.model_status()
        ok(f"LM Studio reachable: {provider.base_url}")
        if status is None:
            fail(f"model not installed/visible to LM Studio: {resolved_model}")
        else:
            ok(f"model available: {status.get('key') or resolved_model}")
            loaded = status.get("loaded_instances") or []
            if loaded:
                ok("model is loaded")
                current_context = (loaded[0].get("config") or {}).get("context_length")
                if current_context and current_context < context_length:
                    warn(
                        f"loaded model context is {current_context}, below requested {context_length}; "
                        "reload it with a larger context or lower --context-length"
                    )
            else:
                warn("model is installed but not loaded; LM Studio may auto-load it on first request")
            max_context = status.get("max_context_length")
            if max_context and context_length > max_context:
                fail(f"requested context {context_length} exceeds model maximum {max_context}")
            reasoning_info = ((status.get("capabilities") or {}).get("reasoning") or {})
            allowed = reasoning_info.get("allowed_options") or []
            if allowed and reasoning not in allowed:
                fail(f"reasoning={reasoning!r} not supported by model; allowed: {', '.join(allowed)}")
            elif allowed:
                ok(f"reasoning mode supported: {reasoning}")
    except (httpx.HTTPError, ValueError) as exc:
        fail(f"LM Studio check failed at {url}: {exc}")

    if source is not None:
        try:
            loaded = ExegateAdapter().load(source)
            ok(f"source parses as ExegateRun: {loaded.envelope.source_path}")
        except (OSError, ValueError, ValidationError) as exc:
            fail(f"source parse check failed: {exc}")

    if failures:
        console.print(f"[bold red]Doctor failed: {failures} error(s), {warnings} warning(s)[/bold red]")
        raise typer.Exit(3)
    console.print(f"[bold green]Doctor passed[/bold green] ({warnings} warning(s))")


@harvest_app.command("exegate")
def harvest_exegate(
    source: Optional[Path] = typer.Argument(None),
    all_sources: bool = typer.Option(False, "--all"),
    source_root: Path = typer.Option(Path("data/parsed"), "--source-root"),
    model: Optional[str] = typer.Option(None, "--model"),
    lm_studio_url: Optional[str] = typer.Option(None, "--lm-studio-url"),
    response_file: Optional[Path] = typer.Option(None, "--response-file"),
    temperature: float = typer.Option(0.1, "--temperature", min=0.0, max=1.0),
    max_output_tokens: int = typer.Option(32768, "--max-output-tokens", min=1024),
    context_length: int = typer.Option(DEFAULT_CONTEXT_LENGTH, "--context-length", min=4096),
    reasoning: ReasoningMode = typer.Option(DEFAULT_REASONING, "--reasoning"),
    timeout: float = typer.Option(600.0, "--timeout", min=1.0),
    out: Path = typer.Option(Path("harvest"), "--out"),
    no_library: bool = typer.Option(False, "--no-library"),
    run_id: Optional[str] = typer.Option(None, "--run-id"),
):
    if all_sources and source is not None:
        raise typer.BadParameter("Provide SOURCE or --all, not both")
    if not all_sources and source is None:
        raise typer.BadParameter("SOURCE is required unless --all is used")
    if all_sources and (response_file or run_id):
        raise typer.BadParameter("--response-file/--run-id are single-source only")
    provider = _provider(
        model=model,
        lm_studio_url=lm_studio_url,
        response_file=response_file,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        context_length=context_length,
        reasoning=reasoning,
        timeout=timeout,
    )
    harvester = LiberHarvester(provider)
    sources = discover_sources(source_root) if all_sources else [source]
    if not sources:
        console.print("[yellow]No Exegate sources found[/yellow]")
        raise typer.Exit(2)
    failures = 0
    for item in sources:
        try:
            _print(
                harvester.run(
                    item,
                    out_root=out,
                    run_id=run_id if len(sources) == 1 else None,
                    write_library=not no_library,
                )
            )
        except (HarvestContractError, ValidationError, ValueError, OSError, httpx.HTTPError) as exc:
            failures += 1
            console.print(f"[bold red]✗[/bold red] {item}: {exc}")
            if len(sources) == 1:
                raise typer.Exit(3)
    if failures:
        raise typer.Exit(3)


@app.command("validate")
def validate(path: Path = typer.Argument(...), provenance: bool = typer.Option(False, "--provenance")):
    failures = 0
    records = 0
    adapter = ExegateAdapter()
    cache = {}
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            failures += 1
            console.print(f"[red]L{lineno}: blank JSONL line[/red]")
            continue
        records += 1
        try:
            record = LoreFragmentRecord.model_validate_json(line)
            if provenance:
                sp = record.provenance[0].source_path
                if sp not in cache:
                    loaded = adapter.load(Path(sp))
                    cache[sp] = None if loaded.envelope.source_sha256 != record.provenance[0].source_sha256 else loaded.document
                    if cache[sp] is None:
                        failures += 1
                        console.print(f"[red]L{lineno}: PROVENANCE STALE - source SHA changed[/red]")
                if cache.get(sp) is not None:
                    for issue in validate_materialized_record(record, source_document=cache[sp]):
                        failures += 1
                        console.print(f"[red]L{lineno}: {issue.code}: {issue.message}[/red]")
        except (ValidationError, OSError, ValueError) as exc:
            failures += 1
            console.print(f"[red]L{lineno}: {exc}[/red]")
    if failures:
        console.print(f"[bold red]Validation failed: {failures} issue(s)[/bold red]")
        raise typer.Exit(3)
    console.print(f"[bold green]✓[/bold green] {records} Lore Fragment record(s) valid")


@app.command("inspect")
def inspect_fragment(
    fragment_id: str,
    library: Path = typer.Option(Path("harvest/library/fragments.jsonl"), "--library"),
):
    for line in library.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if obj.get("fragment_id") == fragment_id:
            console.print_json(json.dumps(obj, ensure_ascii=False))
            return
    console.print(f"[yellow]Fragment not found:[/yellow] {fragment_id}")
    raise typer.Exit(2)


@app.command("version")
def version():
    from . import __version__

    console.print(f"Liber Harvest {__version__}")
