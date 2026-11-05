# Prospective clustered-loss extension protocol v0.1

## Status and separation from the original study

This document governs implementation checks and precision planning for a new prospective extension. It does not amend the completed `freshness-protocol-v0.5` campaign. It uses new seeds, new artifacts and separate analysis. Final extension collection is not authorized by this version.

## Question and estimand

At an equal budget of 10 suppressed update notifications per 100-update trace, how does the temporal pattern of loss affect semantic freshness, stale-episode persistence, observed recovery and resource use? The principal comparison is single-burst loss versus dispersed loss within each frozen policy. Repeated-burst loss is a prespecified secondary temporal pattern.

The extension evaluates the existing mechanisms; it does not claim that invalidation, validation, TTL caching or bounded repair is novel.

## Applications, regimes and transports

The extension retains the three application adapters, three request/update regimes and two Redis transports from the original study. The application-specific semantic oracle and the exogenous event-generation process are unchanged. New seeds are disjoint from engineering, training, validation, variance-planning and final-test seeds in the original campaign.

Redis Pub/Sub and Redis Streams remain synchronous delivery implementations in this experiment. The experiment does not model subscriber disconnection, consumer-group acknowledgment or replay after reconnection. Those behaviors require a separate implementation and protocol.

## Fault schedules

Each trace contains 100 updates. Updates 1–20 and 81–100 are protected, leaving a recovery observation guard at both ends. Faults are selected only among zero-based update indices 20–79.

- `no-fault`: no suppressed notifications.
- `dispersed-10`: 10 nonadjacent suppressed notifications sampled deterministically from the eligible range.
- `single-burst-10`: 10 consecutive suppressed notifications.
- `repeated-bursts-10`: two five-notification bursts separated by at least five delivered update positions.

All fault schedules are deterministic functions of profile and trace seed. Profiles for the same application, regime and seed share the identical exogenous event trace. The fault budget is matched by update-notification count, not elapsed time, because elapsed time is jittered and the scientific contrast concerns temporal clustering at a fixed count of missed invalidation opportunities.

## Frozen policies

The extension reuses training-locked parameters for:

1. conditional validation;
2. fixed TTL;
3. always invalidation; and
4. event invalidation with bounded repair.

These policies span validation, time-based expiry, notification-only invalidation and notification invalidation with a repair bound. No parameter is retuned on extension outcomes. Execution order is inherited from the original counterbalanced allocation and filtered to these four policies.

## Outcomes

The original semantic freshness and resource outcomes are retained:

- freshness-violation proportion;
- mean revision lag and maximum revision lag;
- request wall time;
- operation-thread CPU;
- origin and publisher response bytes; and
- Redis delivery payload bytes.

The extension adds:

- stale-episode count;
- maximum consecutive stale requests;
- maximum elapsed time spanned by a stale episode;
- stale requests observed after the final suppressed notification;
- requests until observed terminal recovery;
- elapsed time until observed terminal recovery; and
- a right-censoring indicator when recovery is not observed before the trace ends.

Observed terminal recovery is defined retrospectively as the first fresh request following the last stale request after the final suppressed notification. It is an application-level observation-window measure, not a claim about internal cache convergence.

## Analysis and collection gates

Application, regime, transport, trace seed and fault profile define a paired block. Results will remain multi-outcome; no scalar utility combines freshness and resource use.

The two engineering seeds are for contract tests and failure detection only. The 10 precision-planning seeds are used to select the final seed count from interval-width targets fixed before their outcomes are examined. Engineering and precision-planning observations will not be pooled with the final extension results.

Before final collection, a new protocol version must freeze:

- the primary contrast and interaction contrasts;
- the confidence level and bootstrap unit;
- the precision target for freshness and recovery outcomes;
- the final seed count and reserved seed range; and
- handling of right-censored recovery observations.

Until that version exists and passes integrity checks, `final_collection_authorized` remains false.
