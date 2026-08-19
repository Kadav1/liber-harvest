"""CLI for running and comparing Liber Harvest model-selection benchmarks."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .benchmark import BENCHMARK_VERSION, SCORE_WEIGHTS, discover_cases
from .benchmark_runtime import (
    BenchmarkPreflightError,
    compare_summaries,
    run_model_benchmark,
)
from .cli import (
    DEFAULT_CONTEXT_LENGTH,
    DEFAULT_REASONING,
    ProviderMode,
    _provider,
)
from .providers.lmstudio import ReasoningMode
from .providers.openai import OpenAIReasoning

app = typer.Typer(
    help="Liber Harvest T01-T11 model-selection benchmark",
    rich_markup_mode=None,
)
console = Console()


@app.command("cases")
def list_cases(
    calibration_root: Path = typer.Option(Path("calibration"), "--calibration-root"),
):
    """List frozen T01-T11 calibration cases and their stress targets."""
    cases = discover_cases(calibration_root)
    table = Table(title=f"Liber Harvest benchmark cases ({BENCHMARK_VERSION})")
    table.add_column("Case")
    table.add_column("Source")
    table.add_column("Purpose")
    table.add_column("Targets")
    for case in cases:
        table.add_row(
            case.case_id,
            case.historical_source_key,
            case.purpose,
            ", ".join(case.targets),
        )
    console.print(table)


@app.command("profile")
def show_profile():
    """Show the automatic scoring weights and ranking formula."""
    table = Table(title=f"Model-selection profile {BENCHMARK_VERSION}")
    table.add_column("Component")
    table.add_column("Weight")
    for key, value in SCORE_WEIGHTS.items():
        table.add_row(key, f"{value:.1f}")
    console.print(table)
    console.print(
        "Automatic selection score: 80% mean compliance + 20% target-check pass percentage."
    )
    console.print(
        "Infrastructure/source failures invalidate ranking instead of scoring the model as zero."
    )
    console.print(
        "Informational semantic targets require human review before final model selection."
    )


@app.command("run")
def run_benchmark(
    provider: ProviderMode = typer.Option(..., "--provider", help="openai or lmstudio."),
    model: Optional[str] = typer.Option(None, "--model", help="Provider model key."),
    label: Optional[str] = typer.Option(None, "--label", help="Human-readable model/config label."),
    cases: Optional[str] = typer.Option(None, "--cases", help="Comma-separated case IDs; default T01-T11."),
    corpus_root: Path = typer.Option(Path("data"), "--corpus-root"),
    calibration_root: Path = typer.Option(Path("calibration"), "--calibration-root"),
    out: Path = typer.Option(Path("benchmark-results"), "--out"),
    lm_studio_url: Optional[str] = typer.Option(None, "--lm-studio-url"),
    openai_base_url: Optional[str] = typer.Option(None, "--openai-base-url"),
    temperature: float = typer.Option(0.1, "--temperature", min=0.0, max=1.0),
    max_output_tokens: int = typer.Option(8192, "--max-output-tokens", min=1024),
    context_length: int = typer.Option(DEFAULT_CONTEXT_LENGTH, "--context-length", min=4096),
    reasoning: ReasoningMode = typer.Option(DEFAULT_REASONING, "--reasoning"),
    openai_reasoning: OpenAIReasoning = typer.Option(OpenAIReasoning.LOW, "--openai-reasoning"),
    lm_studio_structured_output: bool = typer.Option(
        False,
        "--lm-studio-structured-output",
        help=(
            "Use LM Studio /v1/chat/completions JSON-schema output. The model must already be "
            "loaded at --context-length because that endpoint cannot set context per request."
        ),
    ),
    timeout: float = typer.Option(600.0, "--timeout", min=1.0),
    max_repairs: int = typer.Option(1, "--max-repairs", min=0, max=1),
    hardware_note: Optional[str] = typer.Option(None, "--hardware-note"),
):
    """Run selected T01-T11 cases against one live model/provider."""
    if provider == ProviderMode.STATIC:
        raise typer.BadParameter(
            "Model-selection runs require a live model provider; choose openai or lmstudio."
        )
    if provider == ProviderMode.LMSTUDIO:
        if max_output_tokens >= context_length:
            raise typer.BadParameter(
                "--max-output-tokens must be smaller than --context-length for LM Studio "
                f"({max_output_tokens} >= {context_length})"
            )
        if max_output_tokens > context_length / 2:
            console.print(
                "Warning: --max-output-tokens exceeds half of --context-length; large source prompts "
                "may leave too little room for generation or repair."
            )
    elif lm_studio_structured_output:
        raise typer.BadParameter(
            "--lm-studio-structured-output may only be used with --provider lmstudio"
        )

    mode, extraction_provider = _provider(
        provider=provider,
        model=model,
        lm_studio_url=lm_studio_url,
        openai_base_url=openai_base_url,
        response_file=None,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        context_length=context_length,
        reasoning=reasoning,
        openai_reasoning=openai_reasoning,
        timeout=timeout,
    )
    if mode == ProviderMode.LMSTUDIO:
        extraction_provider.structured_output = lm_studio_structured_output

    selected_cases = (
        [part.strip() for part in cases.split(",") if part.strip()]
        if cases
        else None
    )
    model_name = str(getattr(extraction_provider, "model", model or "unknown"))
    model_label = label or model_name

    configuration = {
        "provider": mode.value,
        "model": model_name,
        "label": model_label,
        "temperature": temperature if mode == ProviderMode.LMSTUDIO else None,
        "context_length": context_length if mode == ProviderMode.LMSTUDIO else None,
        "reasoning": str(reasoning) if mode == ProviderMode.LMSTUDIO else None,
        "structured_output": (
            lm_studio_structured_output if mode == ProviderMode.LMSTUDIO else None
        ),
        "openai_reasoning": (
            str(openai_reasoning) if mode == ProviderMode.OPENAI else None
        ),
        "max_output_tokens": max_output_tokens,
        "timeout": timeout,
        "max_repairs": max_repairs,
        "lm_studio_url": (
            getattr(extraction_provider, "base_url", None)
            if mode == ProviderMode.LMSTUDIO
            else None
        ),
        "openai_base_url": (
            getattr(extraction_provider, "base_url", None)
            if mode == ProviderMode.OPENAI
            else None
        ),
        "hardware_note": hardware_note,
    }

    try:
        summary, summary_path = run_model_benchmark(
            provider=extraction_provider,
            provider_name=mode.value,
            model_label=model_label,
            corpus_root=corpus_root,
            calibration_root=calibration_root,
            case_ids=selected_cases,
            out_root=out,
            max_repairs=max_repairs,
            configuration=configuration,
        )
    except BenchmarkPreflightError as exc:
        console.print(str(exc))
        raise typer.Exit(2) from exc

    table = Table(title=f"Liber Harvest model benchmark: {model_label}")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row(
        "Cases completed",
        f"{summary['cases_completed']}/{summary['cases_requested']}",
    )
    selection = summary.get("selection_score")
    table.add_row(
        "Selection score",
        f"{selection:.3f}" if selection is not None else "UNRANKABLE",
    )
    table.add_row(
        "Ranking eligible", "yes" if summary.get("ranking_eligible") else "no"
    )
    table.add_row(
        "Mean compliance", f"{summary['mean_compliance_score']:.3f}"
    )
    table.add_row("Target pass", f"{summary['target_pass_pct']:.3f}%")
    table.add_row("Repair calls", str(summary["total_repair_calls"]))
    table.add_row(
        "Semantic seconds", f"{summary['total_semantic_seconds']:.3f}"
    )
    table.add_row("Summary", str(summary_path))
    console.print(table)
    if summary["cases_failed"]:
        raise typer.Exit(3)


@app.command("compare")
def compare(
    summaries: list[Path] = typer.Argument(
        ..., help="Two or more benchmark summary.json files."
    ),
):
    """Rank benchmark summaries using the model-selection formula."""
    if len(summaries) < 2:
        raise typer.BadParameter("Provide at least two summary.json files")
    rows = compare_summaries(summaries)
    table = Table(title=f"Liber Harvest model leaderboard ({BENCHMARK_VERSION})")
    table.add_column("#")
    table.add_column("Model")
    table.add_column("Provider")
    table.add_column("Eligible")
    table.add_column("Selection")
    table.add_column("Compliance")
    table.add_column("Targets")
    table.add_column("Cases")
    table.add_column("Repairs")
    table.add_column("Semantic s")
    for index, row in enumerate(rows, 1):
        selection = row["selection_score"]
        table.add_row(
            str(index),
            str(row["model"]),
            str(row["provider"]),
            "yes" if row["ranking_eligible"] else "no",
            f"{selection:.3f}" if selection is not None else "—",
            f"{row['mean_compliance_score']:.3f}",
            f"{row['target_pass_pct']:.3f}%",
            f"{row['cases_completed']}/{row['cases_requested']}",
            str(row["repair_calls"]),
            f"{row['semantic_seconds']:.3f}",
        )
    console.print(table)
    console.print(
        "Only ranking-eligible runs should be used for model selection. Inspect informational "
        "semantic targets before final selection."
    )


if __name__ == "__main__":
    app()
