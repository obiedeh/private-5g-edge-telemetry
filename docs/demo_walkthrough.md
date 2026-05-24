# Demo Walkthrough

Run the demo bundle:

```bash
make demo
```

That command reads the bundled raw telemetry in `data/raw/`, tolerates the bad row by quarantining it, and writes a full artifact bundle under `data/demo/`.

Expected outputs:

- `data/demo/curated/private5g_ran_hourly.parquet`
- `data/demo/quarantine/rejected_rows.csv`
- `data/demo/events/private5g_events.ndjson`
- `data/demo/reports/observability_report.json`
- `data/demo/reports/operator_summary.md`
- `data/demo/reports/visual_insights.md`
- `data/demo/reports/figures/01_data_flow.png`
- `data/demo/reports/figures/02_latency_pre_post.png`
- `data/demo/reports/figures/03_congestion_rank.png`
- `data/demo/reports/figures/04_latency_trend.png`
- `data/demo/reports/figures/05_throughput_latency.png`
- `data/demo/reports/figures/06_handover_latency.png`

Operational reading guide:

- `01_data_flow.png` shows raw, quarantined, and curated counts.
- `02_latency_pre_post.png` shows the raw latency spread versus curated hourly p95.
- `03_congestion_rank.png` ranks the most congested cell/slice combinations.
- `04_latency_trend.png` overlays raw samples with the hourly trend for the worst slice.
- `05_throughput_latency.png` shows the throughput-versus-latency tradeoff by slice.
- `06_handover_latency.png` shows the mobility pressure versus latency tradeoff by slice.

The report files are the publishable summary layer. They are intended to be pasted into an ops note, design review, or telecom telemetry brief without extra editing.
