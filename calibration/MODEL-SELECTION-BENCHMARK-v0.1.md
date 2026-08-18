# Liber Harvest Model-Selection Benchmark v0.1

**Status:** APPLICATION-LEVEL BENCHMARK  
**Benchmark version:** `model-selection/0.1`  
**Frozen semantic contract:** `exegate-harvest/0.1.2`  
**Calibration corpus:** T01-T11

This benchmark turns the existing T01-T11 semantic calibration suite into a repeatable model-selection harness for Liber Harvest extraction providers.

It does **not** revise LF-01 through LF-16, the Lore Fragment schemas, or the frozen Exegate Harvest contract.

## Purpose

Generic language-model benchmarks are not sufficient for selecting a Liber Harvest model. The extractor must succeed at the specific behaviors required by the historical-recovery contract:

- preserve source modality;
- separate evidence layers;
- decompose reusable lore without uncontrolled over-splitting;
- isolate obsolete implementation bindings;
- strip pipeline wrappers;
- retain contradictory or abandoned material without canonizing it;
- survive malformed/null legacy metadata;
- emit contract-valid structured JSON;
- support exact provenance materialization;
- minimize repair cycles and manual review.

T01-T11 already stress those behaviors. `model-selection/0.1` adds a repeatable runner, deterministic scoring, timing, provider-repair instrumentation, and cross-model comparison.

## Cases

| Case | Historical source | Principal stress |
|---|---|---|
| T01 | `song_006` | distributed lore, empty structured arrays |
| T02 | `EXE-BUNDLE-V-N-01` | structured symbols/rituals, legacy bindings |
| T03 | `song_001` | generated hooks, atmosphere, modality |
| T04 | `song_008` | legacy theology, evidence layers, span provenance |
| T05 | `song_002` | decomposition and taxonomy |
| T06 | `song_004` | external myth/religion, naming restraint |
| T07 | `song_005` | repeated doctrine, intra-source dedupe |
| T08 | `song_010` | imported terminology, evidence separation |
| T09 | `song_011` | sensory material and intra-source merges |
| T10 | `song_012` | competing interpretations and contradiction |
| T11 | `song_013` | malformed/null legacy metadata |

The historical sources remain runtime corpus inputs and are not copied into the application repository.

## Automatic score

The deterministic compliance score is 0-100:

| Component | Weight |
|---|---:|
| contract validity | 25 |
| coverage | 20 |
| provenance | 15 |
| modality/evidence safety | 15 |
| legacy isolation | 10 |
| exact dedupe | 5 |
| review burden | 5 |
| pipeline-wrapper isolation | 5 |

The aggregate model-selection score is:

```text
80% mean deterministic compliance
+
20% machine-scoreable target-check pass percentage
```

A failed case receives compliance score `0`.

## Important limitation

The automatic score is a **shortlisting mechanism**, not a substitute for semantic judgment.

Some calibration targets cannot be safely reduced to a mechanical score without a gold semantic library. Examples include:

- whether all independently reusable lore was recovered;
- whether a fragment split is semantically ideal rather than merely valid;
- whether a coined term deserves a `name` fragment;
- whether a contradiction was captured at the best conceptual granularity.

Those targets are reported as informational diagnostics where necessary. Final selection should inspect the top-scoring models' T01-T11 outputs.

This is deliberate. The benchmark must not reward a model merely for creating more fragments.

## Runtime corpus layout

```text
data/
├── parsed/
│   ├── song_001.json
│   ├── song_002.json
│   ├── ...
│   └── song_013.json
└── bundles/
    └── EXE-BUNDLE-V-N-01/
        └── exegate_run.json
```

## Commands

The benchmark is installed as both:

```bash
liber-harvest-benchmark
lh-benchmark
```

List cases:

```bash
lh-benchmark cases
```

Show scoring profile:

```bash
lh-benchmark profile
```

Run all T01-T11 against an LM Studio model:

```bash
lh-benchmark run \
  --provider lmstudio \
  --model <lm-studio-model-key> \
  --label qwen3.5-9b-q6k-16k \
  --context-length 16384 \
  --reasoning off \
  --corpus-root data
```

Run selected cases only:

```bash
lh-benchmark run \
  --provider lmstudio \
  --model <model-key> \
  --cases T01,T03,T04,T10
```

For hardware comparisons, record the configuration:

```bash
lh-benchmark run \
  --provider lmstudio \
  --model <model-key> \
  --label bonsai-27b-1bit-16k \
  --context-length 16384 \
  --hardware-note "11 GB VRAM; DDR3 system RAM"
```

Compare completed model runs:

```bash
lh-benchmark compare \
  benchmark-results/<run-a>/summary.json \
  benchmark-results/<run-b>/summary.json \
  benchmark-results/<run-c>/summary.json
```

## Output

Each benchmark run is isolated:

```text
benchmark-results/
└── BMS-<timestamp>-<provider>-<model>/
    ├── T01/
    │   ├── result.json
    │   └── harvest/
    ├── T02/
    │   ├── result.json
    │   └── harvest/
    ├── ...
    ├── T11/
    │   ├── result.json
    │   └── harvest/
    └── summary.json
```

`summary.json` records:

- provider and model/config label;
- cases completed/failed;
- mean compliance score;
- target-check pass percentage;
- aggregate selection score;
- provider repair calls;
- semantic inference time;
- total case runtime;
- per-case result paths.

Each `result.json` records:

- component scores;
- target-specific checks;
- fragment/review counts;
- type/domain/modality/evidence-layer distributions;
- provenance precision distribution;
- legacy-binding leakage;
- pipeline-wrapper leakage;
- exact normalized-lore duplicates;
- provider calls and timing.

## Recommended selection procedure

1. Run exactly the same context/output/repair policy for every candidate where possible.
2. Require all T01-T11 to complete.
3. Rank with `lh-benchmark compare`.
4. Reject models with recurrent contract failures or high repair counts even if they are fast.
5. Manually inspect the top two or three models on T01, T03, T04, T07, and T10.
6. Prefer the smaller/faster model when semantic quality is effectively tied.
7. Freeze the winning model **and exact quantization/configuration label** as the operational Harvest profile.

For constrained hardware, quantization and context length are part of the model identity. Do not compare `Q4` and `Q6` results under the same label.
