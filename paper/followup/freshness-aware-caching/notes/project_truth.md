# Project truth

## Contribution

Dominant contribution type: empirical software/systems study.

The study asks how established cache invalidation and validation policies for mutable web data trade semantic freshness, readiness, origin work and control traffic when update notifications are prompt, delayed, lost or reordered. The central contribution is an end-to-end empirical evaluation across independently implemented web applications. It is not a new invalidation algorithm.

A learned policy is outside the active protocol. It can be considered only in a later study if strong explicit rules leave a measurable sequential decision problem under equal information.

## Evidence boundary

The Software: Practice and Experience submission already reports a 60-request cache pilot in which TTL caching served stale responses and a perfect-signal update-aware rule retained freshness with fewer origin reads than bypass. Those observations motivate this project but are excluded from all new fitting, selection, estimation and hypothesis tests.

Every primary observation for this paper must be collected under the new frozen protocol. The earlier rendering-policy Mac and cloud cohorts are also excluded.

## Active sources

- Manuscript source: `output/doc/manuscript.md`
- Protocol source: `protocol/protocol_v0.5.md`
- Novelty source: `notes/literature_novelty_review_2026-10-29.md`
- Results source: `notes/result_summary.md` and the checksum-bound final analysis artifact from GitHub Actions run `41148624728`

## Venue style

Journal-agnostic empirical software/systems article until a target is selected. Use a conventional Introduction, Related Work, Method, Results, Discussion and Conclusion structure. Venue formatting must not drive the experimental design.

## Stable terminology

- **Fresh response:** served revision satisfies the predeclared application freshness rule at decision time.
- **Stale response:** served revision violates that rule; record revision lag and duration separately.
- **Event-driven invalidation:** an explicit policy using an observable update notification, with notification delay/loss modeled and reported.
- **Trace:** a complete exogenous sequence of requests, updates and notification outcomes shared across policies.
- **Experimental unit:** a full policy execution over a trace in one isolated allocation, not an individual request.

## Selected infrastructure

- Workloads: mutable product service, pinned SvelteKit RealWorld feed and pinned React-admin e-commerce dashboard.
- Notification modes: Redis Pub/Sub and Redis Streams.
- Fault treatment: a study-controlled, machine-readable schedule that retains delay, loss, duplication and reordered-delivery records.
