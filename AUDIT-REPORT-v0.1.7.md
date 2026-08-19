# Liber Harvest v0.1.7 Corrective Audit Report

**Audit status:** PASS  
**Application:** Liber Harvest 0.1.7  
**Frozen semantic contract:** `exegate-harvest/0.1.2`  
**Lore Fragment schema:** `lore-fragment/0.1.2`  
**Benchmark contract:** `model-selection/0.1`  
**Audit date:** 2026-08-19

## 1. Audit purpose

This audit verifies the v0.1.7 corrective release after the T01 local-model run exposed execution-harness defects around context budgeting, full-result repair growth, infrastructure scoring and LM Studio diagnostics.

The audit is intentionally separated from the frozen semantic contract. It evaluates application/runtime behavior and does not revise LF-01 through LF-16.

## 2. Approved corrective scope

v0.1.7 was required to add or correct:

1. benchmark/source preflight before inference;
2. bounded output budgeting and invalid context/output guards;
3. LM Studio HTTP error-body preservation;
4. optional structured JSON output where the provider supports it;
5. deterministic correction before semantic repair;
6. fragment-scoped repair instead of full-result repair;
7. a hard ceiling of two live semantic calls per case;
8. infrastructure/source failures excluded from model-quality scoring;
9. explicit stateless benchmark metadata;
10. regression coverage for the T01 oversized-repair failure;
11. release self-audit before publication.

## 3. Frozen-boundary audit

### PASS

The following semantic/versioned surfaces remain unchanged:

- `ARCHITECTURE-FREEZE-v0.1.2.md`
- `FOLDER-STRUCTURE-FREEZE-v0.1.2.md`
- `contracts/exegate-harvest/v0.1.2/`
- `schemas/v0.1.2/`
- T01-T11 calibration case definitions
- benchmark version `model-selection/0.1`
- LF-01 through LF-16

Only the application/extractor version advances to `0.1.7`.

## 4. Runtime-design audit

### 4.1 Request budgeting — PASS

The benchmark default `--max-output-tokens` is reduced from 32768 to 8192.

For LM Studio benchmark runs:

- `max_output_tokens >= context_length` is rejected before inference;
- output budgets above half the context produce a warning;
- a 16K local profile is documented with 4096 output tokens as the conservative starting point.

This directly prevents the invalid 32768-output / 16384-context configuration exposed by T01.

### 4.2 Stateless benchmark execution — PASS

Every benchmark case records:

```json
"session_mode": "stateless"
```

No benchmark case passes prior-case conversation state to the provider. Provider preflight/configuration metadata is recorded in the suite summary.

### 4.3 Semantic-call ceiling — PASS

Each source permits:

```text
1 extraction
+
at most 1 fragment-scoped repair
=
at most 2 live semantic calls
```

Provider-internal JSON syntax-repair calls were removed. `max_repairs` is restricted to 0 or 1.

### 4.4 Full-result repair removal — PASS

The old behavior could resend:

- the complete source envelope;
- the complete large invalid candidate;
- validation errors;
- the full system contract.

v0.1.7 removes that path.

A model repair is eligible only when **every** Pydantic validation error is local to one or more fragment items. Only those fragments and directly associated coverage entries are sent for repair.

Mixed root-level + fragment-level validation failures do not consume the single repair call.

### 4.5 Deterministic correction — PASS

`src/liber_harvest/corrections.py` performs only source/contract-provable corrections, including:

- canonical source path/hash/title/pipeline identity;
- safe scalar-pointer parent correction when the exact excerpt proves the parent scalar;
- Circle derivation from the top-level provenance pointer;
- `content.details` shape normalization;
- internal derivation-operation consistency;
- removal of fragments whose complete provenance resolves to empty/null source material;
- corresponding coverage/discard normalization;
- safe downgrade of generated-hook/generated-phrase provenance from asserted to proposed when necessary.

The deterministic corrector does **not** repair semantic interpretation, invent legacy bindings, decide canon, or manufacture lore.

### 4.6 Concept-key repair integrity — PASS after audit fix

Initial implementation preserved the original concept key during fragment repair. Audit identified that this could preserve an invalid key and prevent a legitimate schema repair.

Correction applied:

- repaired `concept_key` may replace the invalid original key;
- top-level coverage references are remapped from the old key to the repaired key.

Regression coverage was added.

### 4.7 Deterministic validation ownership — PASS

`validate_result_against_source` failures are no longer delegated back to a model. Final source identity, exact provenance resolution, materialization, hashes and final validation remain deterministic Harvest responsibilities.

## 5. LM Studio provider audit

### PASS

v0.1.7 preserves the native `/api/v1/chat` path as the default local mode and adds:

- response-body-preserving `LMStudioHTTPError` diagnostics;
- provider benchmark preflight;
- output/context budget validation;
- optional JSON-Schema-constrained structured output through the compatible chat-completions path;
- exact loaded-instance binding for structured benchmark mode at the requested context length.

Audit identified and fixed a reproducibility risk where structured mode could have addressed a generic model key even though context length is controlled by the loaded instance. Structured mode now binds an exact matching loaded instance during preflight and uses that instance ID for inference.

## 6. Benchmark integrity audit

### 6.1 Full suite source preflight — PASS

All selected T01-T11 sources are resolved and parsed before inference begins. A missing T02 `EXE-BUNDLE-V-N-01` therefore aborts the suite before T01 consumes model time.

### 6.2 Failure classification — PASS

Benchmark outcomes distinguish:

- `completed`
- `contract_failed`
- `model_failed`
- `infrastructure_failed`
- `source_missing`

`contract_failed` and `model_failed` remain model-scorable failures.

`infrastructure_failed` and `source_missing` do not receive fabricated model-quality zeroes. Instead the suite becomes:

```json
{
  "benchmark_valid": false,
  "ranking_eligible": false,
  "selection_score": null
}
```

Unrankable runs sort below ranking-eligible runs in comparison output.

### 6.3 T01 oversized-repair regression — PASS

Regression coverage constructs a candidate with a very large unrelated valid fragment and one invalid target fragment. The repair subset contains only the invalid target and excludes the unrelated large payload, proving that v0.1.7 no longer reproduces the original whole-candidate repair growth pattern.

## 7. Verification evidence

### Functional verification

Temporary GitHub Actions verification was used solely as release evidence and is excluded from the final release tree.

Canonical packaging verification:

- workflow run: `32216958359`
- job: `95960167891`
- runner: GitHub Actions `ubuntu-24.04`
- Python: `3.12.14`
- pytest: **51 passed in 0.74s**
- changed-file Ruff: **PASS**
- bytecode compilation: **PASS**
- CLI smoke: **PASS**
- wheel build: **PASS**

CLI smoke confirmed:

```text
Liber Harvest 0.1.7
lh-benchmark --help
lh-benchmark profile
lh-benchmark cases
```

Canonical verification wheel:

```text
liber_harvest-0.1.7-py3-none-any.whl
SHA-256: c74ae7c5127b3c4f48049c280988294c74f7db547763a5abae8ce07e8a2ad00c
```

## 8. Lint audit note

Changed v0.1.7 Python files pass Ruff with `B008` explicitly excluded for Typer command signatures. `B008` warns about function calls in defaults; Typer intentionally uses `typer.Option(...)` / `typer.Argument(...)` in function signatures. Other reported v0.1.7 lint issues were corrected rather than suppressed.

## 9. Packaging audit note

The wheel builds successfully. Setuptools emits a non-blocking forward deprecation warning for the existing TOML-table form of `project.license`, with a stated future removal horizon in 2027. This is pre-existing packaging maintenance debt and is not a v0.1.7 functional blocker.

## 10. Audit findings and disposition

| Finding | Severity | Disposition |
|---|---|---|
| 32768 output budget allowed inside 16384 context | High | Fixed |
| Full-result repair could exceed local context | High | Fixed |
| Provider-internal syntax repair violated two-call ceiling | High | Fixed |
| Missing T02 source discovered only after earlier inference | High | Fixed by suite preflight |
| Infrastructure failures could lower model score | High | Fixed; run becomes unrankable |
| LM Studio 400 body hidden | Medium | Fixed |
| Repaired invalid concept key could be forcibly restored | Medium | Found in audit; fixed + regression |
| Mixed root/fragment errors could consume fragment repair | Medium | Found in audit; fixed + regression |
| Structured mode could use generic model key instead of exact loaded context instance | Medium | Found in audit; fixed + regression |
| Setuptools license-table deprecation warning | Low / future | Recorded; non-blocking |

## 11. Final verdict

**PASS — v0.1.7 is suitable for clean publication.**

The corrective release materially hardens local-model execution without altering the frozen lore semantics. The original T01 failure mode is now guarded at request budgeting, repair scope, source preflight, diagnostics and regression-test levels.

Publication requirements after this audit:

1. update release/integrity manifests;
2. exclude temporary verification workflow/PR artifacts;
3. publish one clean v0.1.7 commit directly on top of v0.1.6;
4. verify the final diff contains no contract/schema/calibration-case mutations.
