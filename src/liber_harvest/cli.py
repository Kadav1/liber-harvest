"""Command-line interface for the standalone Liber Harvest tool."""
from __future__ import annotations

import json
import os
from enum import StrEnum
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
from .providers.openai import OpenAIProvider, OpenAIReasoning
from .providers.static import StaticProvider
from .validation import validate_materialized_record

app = typer.Typer(help="Liber Harvest: provenance-preserving historical lore recovery", rich_markup_mode=None)
harvest_app = typer.Typer(help="Run frozen harvest pipelines", rich_markup_mode=None)
app.add_typer(harvest_app, name="harvest")
console = Console()

DEFAULT_LM_STUDIO_URL = "http://127.0.0.1:1234"
DEFAULT_LM_STUDIO_MODEL = "qwen/qwen3.6-35b-a3b"
DEFAULT_OPENAI_URL = "https://api.openai.com/v1"
DEFAULT_OPENAI_MODEL = "gpt-5.6"
DEFAULT_CONTEXT_LENGTH = 65536
DEFAULT_REASONING = ReasoningMode.OFF
DEFAULT_OPENAI_REASONING = OpenAIReasoning.LOW


class ProviderMode(StrEnum):
    OPENAI = "openai"
    LMSTUDIO = "lmstudio"
    STATIC = "static"


def _provider_help() -> str:
    return (
        "No extraction provider selected. Choose --provider openai, "
        "--provider lmstudio, or supply --response-file for static/offline materialization. "
        "You may also set LIBER_HARVEST_PROVIDER=openai|lmstudio."
    )


def _resolve_provider_mode(
    provider: ProviderMode | None,
    response_file: Path | None,
) -> ProviderMode:
    if response_file is not None:
        if provider is not None and provider != ProviderMode.STATIC:
            raise typer.BadParameter("--response-file may only be used with --provider static (or with no --provider)")
        return ProviderMode.STATIC

    raw = provider.value if provider is not None else os.getenv("LIBER_HARVEST_PROVIDER")
    if not raw:
        raise typer.BadParameter(_provider_help())
    try:
        mode = ProviderMode(raw)
    except ValueError as exc:
        raise typer.BadParameter(
            f"Unknown provider {raw!r}; choose openai, lmstudio, or static"
        ) from exc
    if mode == ProviderMode.STATIC:
        raise typer.BadParameter("--provider static requires --response-file FILE")
    return mode


def _provider(
    *,
    provider: ProviderMode | None,
    model: Optional[str],
    lm_studio_url: Optional[str],
    openai_base_url: Optional[str],
    response_file: Optional[Path],
    temperature: float,
    max_output_tokens: int,
    context_length: int,
    reasoning: ReasoningMode,
    openai_reasoning: OpenAIReasoning,
    timeout: float,
):
    mode = _resolve_provider_mode(provider, response_file)
    if mode == ProviderMode.STATIC:
        assert response_file is not None
        return mode, StaticProvider.from_file(response_file)

    if mode == ProviderMode.OPENAI:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise typer.BadParameter(
                "OpenAI provider requires OPENAI_API_KEY. Export it in your shell before harvesting."
            )
        resolved_model = model or os.getenv("LIBER_HARVEST_MODEL") or DEFAULT_OPENAI_MODEL
        url = openai_base_url or os.getenv("LIBER_HARVEST_OPENAI_BASE_URL", DEFAULT_OPENAI_URL)
        return mode, OpenAIProvider(
            api_key=api_key,
            base_url=url,
            model=resolved_model,
            reasoning=openai_reasoning,
            max_output_tokens=max_output_tokens,
            timeout=timeout,
        )

    resolved_model = model or os.getenv("LIBER_HARVEST_MODEL") or DEFAULT_LM_STUDIO_MODEL
    url = lm_studio_url or os.getenv("LIBER_HARVEST_LM_STUDIO_URL", DEFAULT_LM_STUDIO_URL)
    return mode, LMStudioProvider(
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


def _network_message(mode: ProviderMode, exc: Exception) -> str:
    if mode == ProviderMode.LMSTUDIO:
        return (
            f"LM Studio is not reachable at the configured endpoint ({exc}). "
            "Start/check the LM Studio server, run `liber-harvest doctor --provider lmstudio`, "
            "or choose `--provider openai` to harvest without LM Studio."
        )
    if mode == ProviderMode.OPENAI:
        return (
            f"OpenAI API is not reachable ({exc}). Check network access and OPENAI_API_KEY, then run "
            "`liber-harvest doctor --provider openai`."
        )
    return str(exc)


@app.command("providers")
def list_providers():
    """List semantic-extraction backends available to Liber Harvest."""
    table = Table(title="Liber Harvest providers")
    table.add_column("Provider")
    table.add_column("Live inference")
    table.add_column("Requirement")
    table.add_row("openai", "Hosted", "OPENAI_API_KEY")
    table.add_row("lmstudio", "Local", "LM Studio server")
    table.add_row("static", "None", "--response-file FILE")
    console.print(table)
    console.print("No live provider is selected implicitly. Use --provider or LIBER_HARVEST_PROVIDER.")


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
    provider: Optional[ProviderMode] = typer.Option(None, "--provider", help="Provider to check."),
    model: Optional[str] = typer.Option(None, "--model", help="Provider model key."),
    lm_studio_url: Optional[str] = typer.Option(None, "--lm-studio-url"),
    openai_base_url: Optional[str] = typer.Option(None, "--openai-base-url"),
    context_length: int = typer.Option(DEFAULT_CONTEXT_LENGTH, "--context-length", min=4096),
    reasoning: ReasoningMode = typer.Option(DEFAULT_REASONING, "--reasoning"),
    openai_reasoning: OpenAIReasoning = typer.Option(DEFAULT_OPENAI_REASONING, "--openai-reasoning"),
    response_file: Optional[Path] = typer.Option(None, "--response-file"),
    source: Optional[Path] = typer.Option(None, "--source", help="Optional Exegate JSON/bundle to parse-check."),
    out: Path = typer.Option(Path("harvest"), "--out"),
):
    """Check workspace, optional source parsing, and the selected extraction provider."""
    failures = 0
    warnings = 0

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

    if source is not None:
        try:
            loaded = ExegateAdapter().load(source)
            ok(f"source parses as ExegateRun: {loaded.envelope.source_path}")
        except (OSError, ValueError, ValidationError) as exc:
            fail(f"source parse check failed: {exc}")

    selected_raw = provider.value if provider is not None else os.getenv("LIBER_HARVEST_PROVIDER")
    if response_file is not None:
        selected_raw = ProviderMode.STATIC.value

    if not selected_raw:
        warn("no extraction provider selected; provider-specific checks skipped")
        console.print("Use `liber-harvest providers` to see available modes.")
    else:
        try:
            selected = ProviderMode(selected_raw)
        except ValueError:
            fail(f"unknown configured provider: {selected_raw!r}")
            selected = None

        if selected == ProviderMode.STATIC:
            if response_file is None:
                fail("static provider requires --response-file FILE")
            else:
                try:
                    StaticProvider.from_file(response_file)
                    ok(f"static response file parses: {response_file}")
                except (OSError, ValueError, json.JSONDecodeError) as exc:
                    fail(f"static response file is invalid: {exc}")

        elif selected == ProviderMode.OPENAI:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                fail("OPENAI_API_KEY is not configured")
            else:
                resolved_model = model or os.getenv("LIBER_HARVEST_MODEL") or DEFAULT_OPENAI_MODEL
                url = openai_base_url or os.getenv("LIBER_HARVEST_OPENAI_BASE_URL", DEFAULT_OPENAI_URL)
                openai_provider = OpenAIProvider(
                    api_key=api_key,
                    model=resolved_model,
                    base_url=url,
                    reasoning=openai_reasoning,
                    timeout=30.0,
                )
                try:
                    status = openai_provider.model_status()
                    ok(f"OpenAI API reachable: {openai_provider.base_url}")
                    if status is None:
                        fail(f"OpenAI model is not available to this API key: {resolved_model}")
                    else:
                        ok(f"OpenAI model available: {status.get('id') or resolved_model}")
                except (httpx.HTTPError, ValueError) as exc:
                    fail(f"OpenAI provider check failed: {exc}")

        elif selected == ProviderMode.LMSTUDIO:
            url = lm_studio_url or os.getenv("LIBER_HARVEST_LM_STUDIO_URL", DEFAULT_LM_STUDIO_URL)
            resolved_model = model or os.getenv("LIBER_HARVEST_MODEL") or DEFAULT_LM_STUDIO_MODEL
            lm_provider = LMStudioProvider(
                base_url=url,
                model=resolved_model,
                context_length=context_length,
                reasoning=reasoning,
                timeout=30.0,
                api_token=os.getenv("LIBER_HARVEST_LM_STUDIO_TOKEN"),
            )
            try:
                status = lm_provider.model_status()
                ok(f"LM Studio reachable: {lm_provider.base_url}")
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
                    if allowed and str(reasoning) not in allowed:
                        fail(f"reasoning={str(reasoning)!r} not supported by model; allowed: {', '.join(allowed)}")
                    elif allowed:
                        ok(f"reasoning mode supported: {reasoning}")
            except (httpx.HTTPError, ValueError) as exc:
                fail(f"LM Studio check failed at {url}: {exc}")

    if failures:
        console.print(f"[bold red]Doctor failed: {failures} error(s), {warnings} warning(s)[/bold red]")
        raise typer.Exit(3)
    console.print(f"[bold green]Doctor passed[/bold green] ({warnings} warning(s))")


@harvest_app.command("exegate")
def harvest_exegate(
    source: Optional[Path] = typer.Argument(None, help="Exegate JSON, Markdown, or bundle directory."),
    all_sources: bool = typer.Option(False, "--all", help="Harvest every song_*.json under --source-root."),
    source_root: Path = typer.Option(Path("data/parsed"), "--source-root", help="Batch input root used by --all."),
    provider: Optional[ProviderMode] = typer.Option(None, "--provider", help="openai, lmstudio, or static."),
    model: Optional[str] = typer.Option(None, "--model", help="Model for the selected live provider."),
    lm_studio_url: Optional[str] = typer.Option(None, "--lm-studio-url"),
    openai_base_url: Optional[str] = typer.Option(None, "--openai-base-url"),
    response_file: Optional[Path] = typer.Option(None, "--response-file", help="Saved extraction JSON; implies static provider."),
    temperature: float = typer.Option(0.1, "--temperature", min=0.0, max=1.0, help="LM Studio sampling temperature."),
    max_output_tokens: int = typer.Option(32768, "--max-output-tokens", min=1024),
    context_length: int = typer.Option(DEFAULT_CONTEXT_LENGTH, "--context-length", min=4096, help="LM Studio request context."),
    reasoning: ReasoningMode = typer.Option(DEFAULT_REASONING, "--reasoning", help="LM Studio reasoning mode."),
    openai_reasoning: OpenAIReasoning = typer.Option(DEFAULT_OPENAI_REASONING, "--openai-reasoning", help="OpenAI reasoning effort."),
    timeout: float = typer.Option(600.0, "--timeout", min=1.0),
    out: Path = typer.Option(Path("harvest"), "--out"),
    no_library: bool = typer.Option(False, "--no-library"),
    run_id: Optional[str] = typer.Option(None, "--run-id"),
):
    """Harvest one Exegate source or batch-harvest data/parsed/song_*.json."""
    if all_sources and source is not None:
        raise typer.BadParameter("Provide SOURCE or --all, not both")
    if not all_sources and source is None:
        raise typer.BadParameter("SOURCE is required unless --all is used")
    if all_sources and (response_file or run_id):
        raise typer.BadParameter("--response-file/--run-id are single-source only")

    mode, extraction_provider = _provider(
        provider=provider,
        model=model,
        lm_studio_url=lm_studio_url,
        openai_base_url=openai_base_url,
        response_file=response_file,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        context_length=context_length,
        reasoning=reasoning,
        openai_reasoning=openai_reasoning,
        timeout=timeout,
    )
    harvester = LiberHarvester(extraction_provider)
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
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            failures += 1
            console.print(f"[bold red]✗[/bold red] {item}: {_network_message(mode, exc)}")
            if len(sources) == 1:
                raise typer.Exit(3)
        except httpx.HTTPStatusError as exc:
            failures += 1
            console.print(f"[bold red]✗[/bold red] {item}: provider HTTP error: {exc}")
            if len(sources) == 1:
                raise typer.Exit(3)
        except (HarvestContractError, ValidationError, ValueError, OSError) as exc:
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
