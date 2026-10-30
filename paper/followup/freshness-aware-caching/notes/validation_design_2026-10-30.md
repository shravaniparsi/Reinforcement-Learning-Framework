# Held-out validation design

Date: 2026-10-30

The validation partition uses the five prospectively reserved seeds 200 through
204. It runs all eight locked policies across three workloads, three regimes, all
12 frozen fault profiles and both Redis transports. This produces 1,080 hosted
allocation blocks and 8,640 full-trace units. Each block uses the frozen
SHA-256-derived policy permutation and a fresh process and complete reset for
each policy.

No candidate grid is reopened. Fixed-TTL, stale-while-revalidate, event-repair
and write-reactive options must exactly match their checksum-bound training
locks. The full fault grid is collected to exercise levels that were deliberately
excluded from fitting and to expose any schedule-specific implementation failure.

Confirmation is evaluated separately for each workload, regime and fitted policy
family. Time-policy confirmation uses the five no-fault Pub/Sub traces, matching
the fitting condition. Event-policy confirmation uses 40 traces spanning the
four fitting profiles, both transports and five validation seeds. A lock is
confirmed when its mean trace-level freshness-violation proportion is no more
than 0.01 above its recorded training mean. Every planned block must pass and
every options file must match the lock. The rule is an out-of-sample progression
guardrail, not a claim that the selected candidate is optimal.

If any guardrail fails, the failure is retained and final-test progression stops.
Validation outcomes cannot refit a parameter or select an alternative candidate.
Any redesign would require a new versioned protocol and new disjoint evidence
partitions. Variance planning and final-test collection remain prohibited until
the validation report passes this frozen rule.
