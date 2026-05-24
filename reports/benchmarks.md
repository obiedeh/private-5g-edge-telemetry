# Pipeline benchmarks

Measured numbers. Not FPS or GPU utilisation — this isn't an inference workload —
but the equivalent for a telemetry-intelligence layer: how fast it ingests, how it
behaves under corrupted input, and how long the full evidence-regeneration chain
takes on a clean run. Refresh by running `make benchmarks`.

## Headline

| Benchmark | Result |
|---|---|
| **Synthetic-generator throughput** | 10,455 rows / sec (43,200 rows in 4.132 s) |
| **Schema quarantine throughput** | 168,237 rows / sec (8,640 rows, 5.0% rejected at 5.0% corruption) |
| **End-to-end regeneration** | 16.124 s (both scenarios + both business cases + portal) |
| **Determinism (seed 42, two runs)** | byte-identical metrics JSON |

## What this measures

- **Ingest throughput** is the synthetic generator producing schema-conformant rows. Sets a floor for how fast the pipeline would handle telemetry under load. Production ingest off a real RAN feed would obviously be capped by the feed itself.
- **Quarantine throughput** is the fail-soft schema validator separating clean rows from corrupted rows. Run against a fixture with 5% corruption mixed across out-of-range, missing identifiers, and bad timestamps. The validator never crashes.
- **End-to-end regeneration** is the wall-clock for re-creating every committed evidence artifact: both scenarios, both business cases, the portal. Plus tests + lint + typecheck (separate, via `make verify`), the full reproducibility gate ships in under a minute on a developer laptop.
- **Determinism** is a SHA-256 check on the two scenario `scenario_metrics.json` files after re-running at seed 42 from scratch. Identical hash = identical bytes = the answer is the model, not the noise floor.

## Stage breakdown

| Stage | Wall-clock (s) |
|---|---:|
| Manufacturing scenario | 0.901 |
| Pharma scenario | 1.295 |
| Manufacturing business case | 8.408 |
| Pharma business case | 5.514 |
| Portal | 0.006 |
| **Total** | **16.124** |

## Raw determinism hashes (SHA-256)

- Manufacturing run A: `1b0610d91c3f7809…`
- Manufacturing run B: `1b0610d91c3f7809…` (match: True)
- Pharma run A: `93cd5fd156b91e6e…`
- Pharma run B: `93cd5fd156b91e6e…` (match: True)

## Environment

Single-process Python, no parallelism. Same hardware on every `make benchmarks` run.
Raw numbers in [`benchmarks.json`](benchmarks.json).
