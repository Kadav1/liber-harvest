# Calibration corpus

These directories freeze the semantic calibration cases used to ratify v0.1.2. Historical source files remain external legacy-corpus inputs; synthetic regression fixtures live under `tests/fixtures/`.

T01-T11 remain unchanged as the frozen semantic calibration identities. Application-level model benchmarking is layered on top of them through:

- `MODEL-SELECTION-BENCHMARK-v0.1.md`
- `model-selection-profile-v0.1.json`
- `liber-harvest-benchmark` / `lh-benchmark`

The benchmark does not revise the frozen `exegate-harvest/0.1.2` contract. Generated benchmark output belongs under `benchmark-results/` and is runtime evidence, not calibration source material.
