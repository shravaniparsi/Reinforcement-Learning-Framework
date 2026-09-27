# Final study data dictionary

Each JSONL line is one browser action observation. Each test unit contains 72 observations: three applications, two CPU emulation rates, two browser priming labels, two rendering actions and three cases or repetitions per cell.

## Identification and design fields

- `session_id`: Mac test session or hosted allocation identifier.
- `stage`: Study partition label. Released observations are final test records.
- `index`: Execution position within the unit schedule.
- `pair_id`: Identifier shared by the matched SSR and CSR observations.
- `application`: `catalog`, `articles` or `external` workflow.
- `case_id` and `repetition`: Workload case and repeated-case identifiers.
- `cpu_rate`: Browser CPU emulation multiplier, 1 or 4.
- `cache`: Experimental priming label, `cold` or `warm`; this does not assert reset of every cache layer.
- `action`: `ssr` or `csr` rendering treatment.

## Validation fields

- `status`: Collection outcome.
- `correctness`: Whether declared content and functional checks passed.
- `errors`: Retained collection errors; final released observations have none.
- `external_requests`: Unexpected external browser requests; final released observations have none.
- `content_sha256`: Hash of expected application content.
- `interaction`: Scripted functional check when applicable.

## Measurement fields

- `metrics.mount_hydration_ms`: Primary navigation-to-application-marker endpoint in milliseconds. Despite the historical field name, this is elapsed time from the document performance origin, not isolated hydration duration.
- `metrics.paint_observation_end_ms`: End of the retained paint-observation window.
- `metrics.fcp_ms` and `metrics.lcp_ms`: Browser paint diagnostics. They are not substituted for the primary endpoint.
- `metrics.ttfb_ms`: Time to first byte diagnostic.
- `metrics.server_cpu_seconds` and `metrics.server_cpu_window_seconds`: Server CPU and observation-window diagnostics.
- `metrics.transfer_bytes`: Recorded transfer bytes.
- `backend`: Application-specific backend timing and query metadata where available.

The `units.json` files provide the complete schedule and provenance extract for each cohort. `frozen-actions.json` contains every evaluated policy decision. `expected-results.json` contains the target numerical summaries checked by `reproduce_scores.py`.
