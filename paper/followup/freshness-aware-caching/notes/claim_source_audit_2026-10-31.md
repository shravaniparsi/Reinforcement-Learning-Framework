# Claim-to-source audit

Date: 31 October 2026

Scope: every externally supported claim in `output/doc/manuscript.md` after the
confirmatory-results draft. Study-generated results were checked against the
analysis tables separately and are outside this literature audit.

## Method and counts

The proposer mapped each claim to primary text or an authoritative technical
record. An independent skeptic then defaulted to rejection and re-read each
pairing. The initial audit contained 20 claim units:

- 16 confirmed;
- 2 partial;
- 2 rejected; and
- 0 blocked.

Both partial items and both rejected items were corrected in the manuscript.
The post-correction state has no unresolved claim-to-source pairing in the
audited set.

## Resolution log

| Location and claim | Initial outcome | Resolution and carrying source |
|---|---|---|
| Introduction and Section 2.1: HTTP freshness, staleness and conditional validation | Confirmed | RFC 9111 defines fresh and stale stored responses and validation through conditional requests. [RFC 9111](https://www.rfc-editor.org/rfc/rfc9111.html) |
| Introduction and Section 2.1: bounded stale serving during background revalidation | Confirmed | RFC 5861 states that stale-while-revalidate can return a stale response while revalidating it in the background. [RFC 5861](https://www.rfc-editor.org/rfc/rfc5861.html) |
| Introduction: the field's “remaining empirical question” | Rejected | The cited set cannot establish a unique remaining question for the field. The sentence now names the exact combination absent from these cited studies rather than making an exhaustive field-wide claim. |
| Section 2.2: invalidation versus adaptive TTL and polling | Confirmed | Cao and Liu report comparable traffic, server workload and average response time for invalidation and adaptive TTL, while polling adds control messages and latency. [Primary paper](https://doi.org/10.1109/12.675713) |
| Section 2.2: timestamp-based stale-result detection | Confirmed | Alici et al. compare result-generation times with posting-list and document update times. [Primary paper](https://doi.org/10.1145/2009916.2010046) |
| Section 2.2: workload-informed TTL mechanisms | Confirmed | Sazoglu et al. evaluate time-, frequency- and click-based TTL policies and hybrids. [Primary paper](https://doi.org/10.1145/2505515.2507886) |
| Section 2.2: deep reinforcement learning for TTL cache utility under changing popularity | Confirmed | Cho et al. apply deep reinforcement learning to utility-driven TTL caching under time-varying request traffic. [ETRI record](https://ksp.etri.re.kr/ksp/article/read?id=65200) |
| Section 2.2: database-assisted transparent invalidation | Confirmed | Ji et al. modify database outputs and add cache-side invalidation indexes for precise application-cache invalidation. [arXiv manuscript](https://arxiv.org/abs/2311.02384) |
| Section 2.2: cited prior work does not jointly evaluate complete responses under the study's notification treatments | Partial | Inspection supports the bounded comparison, but the original wording was broader than the cited set. It now says “none of these cited studies jointly evaluates” the named combination. |
| Section 2.3 and Discussion: update-or-invalidate costs depend on workload and resource costs | Confirmed | Mao et al. model update, invalidation and miss costs and evaluate workload-dependent adaptive selection. [HotNets paper](https://conferences.sigcomm.org/hotnets/2024/papers/hotnets24-21.pdf) |
| Section 2.3: exact write-reactive action rule | Partial | Mao et al.'s evaluation sentence reverses the actions implied by its cost derivation and explanation. The manuscript now discloses the inconsistency and follows the cost-minimizing direction. |
| Section 2.4: Pub/Sub uses at-most-once delivery and can permanently lose an unhandled message | Confirmed | Redis states that a message the subscriber cannot handle is “forever lost.” [Redis Pub/Sub documentation](https://redis.io/docs/latest/develop/pubsub/) |
| Section 2.4: Streams retains entries and supports acknowledgment, pending-entry inspection and recovery | Confirmed | Redis documents stream retention, `XACK`, pending entries and claiming unprocessed messages. [Redis Streams documentation](https://redis.io/docs/latest/develop/data-types/streams/) |
| Section 4.1: SvelteKit RealWorld provenance | Rejected | The named external workload lacked a citation. A pinned repository entry for commit `df796708040f5200ec572b28ab7f88ecee5794dd` was added and cited. [Pinned source](https://github.com/sveltejs/realworld/tree/df796708040f5200ec572b28ab7f88ecee5794dd) |
| Section 4.1: React-admin demo provenance | Confirmed | The cited repository contains the `examples/demo` application at commit `0c33d9c3c27cc4bf97e11f56080c5bfe182f2f2a`. [Pinned source](https://github.com/marmelab/react-admin/tree/0c33d9c3c27cc4bf97e11f56080c5bfe182f2f2a/examples/demo) |

## Corrections carried forward as warnings

1. Do not describe the empirical gap as the field's single remaining question.
   Keep the novelty claim bounded to the named cited studies and the exact joint
   evaluation performed here.
2. Do not quote Mao et al.'s Section 3.4 action labels as an unambiguous rule.
   Preserve the disclosure and the cost-minimizing interpretation.
3. Keep both external workload repositories pinned by commit and cited wherever
   their provenance is introduced.

## Source-verification boundary

The Cho et al. pairing was confirmed from the institutional metadata and
abstract record; full text was not required for the limited claim made in the
manuscript. Ji et al. is cited as a preprint rather than as peer-reviewed final
publication. No source in the audited set was fabricated, and no author-order or
wrong-population error was found.
