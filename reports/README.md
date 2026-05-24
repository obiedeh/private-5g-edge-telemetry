# Reports

This directory contains static sample reports and generated Markdown summaries for the simulated private 5G telemetry pipeline.

Reports are intentionally data-first:

- They summarize CSV or synthetic telemetry, not live network integrations.
- They expose AI-RAN, edge AI, and observability signals such as congestion ratio, latency pressure, spectral efficiency, and AI-RAN efficiency.
- They are suitable as portfolio artifacts for telemetry engineering workflows.

Run:

```bash
make run-sample
```

The command refreshes `reports/sample_pipeline_report.md` and writes structured outputs under `data/`.
