# When Invalidation Messages Fail: An End-to-End Study of Cache Freshness in Mutable Web Applications

Status: manuscript skeleton; no new study results collected.

## Abstract

To be written after the protocol is frozen and the final results are available. The abstract will state the evaluated workloads, policy information assumptions, freshness rule, experimental units and separate freshness, latency and origin-work findings.

## 1. Introduction

Web caches can reduce latency and origin work by reusing earlier responses, but mutable data make reuse a correctness decision as well as a performance decision. A policy that appears faster may simply tolerate stale content. Established approaches include conditional validation, time-to-live rules, stale-while-revalidate, explicit invalidation, cache updates and write-reactive selection between updating and invalidating. Their end-to-end behavior depends on whether update notifications arrive promptly and reliably.

This study asks how those policies behave when notifications are delayed, lost or reordered. It will connect origin revisions to browser-visible content across independently implemented web applications and report semantic freshness, stale duration, readiness, origin work and control traffic separately. The contribution is empirical evidence about robustness and repair under imperfect delivery, rather than a new invalidation algorithm.

The submitted Software: Practice and Experience study provides pilot motivation but no observations for the new estimates. All estimates in this article will come from a new prospective protocol with trace-level experimental units and held-out final tests.

## 2. Background and related work

Planned topics: HTTP freshness and validation; adaptive TTL; event-driven invalidation and update; transparent database-assisted invalidation; write-reactive update-or-invalidate rules; stale-while-revalidate; Redis Pub/Sub and Streams delivery semantics; semantic freshness oracles; and evaluation under dependent request sequences.

## 3. Research questions and decision model

Use the frozen research questions and constrained reporting contract from the final protocol. The central factor is notification delivery quality. A learned policy is outside the active study.

## 4. Workloads and policies

Describe application provenance, update/request traces, information available to each policy and isolation/reset behavior.

## 5. Experimental design and analysis

Define experimental units, partitions, randomization, endpoints, failure rules, sample planning and hierarchical analysis.

## 6. Results

Reserved for locked-study outcomes. Do not draft numeric claims from the prior pilot.

## 7. Discussion and threats to validity

Separate observed policy tradeoffs from deployment recommendations. Address trace representativeness, notification assumptions, shared hosted infrastructure, endpoint validity and transport across workloads.

## 8. Conclusion

To be written from the final claim hierarchy.

## Data and code availability

To be completed after a curated versioned release exists.

## References

Verified seed references are maintained in `references/verified_sources.bib`. The bibliography includes the core standards and scholarly competitors, plus pinned infrastructure sources for Redis and React-admin. The Ji et al. publication status must be rechecked before submission.
