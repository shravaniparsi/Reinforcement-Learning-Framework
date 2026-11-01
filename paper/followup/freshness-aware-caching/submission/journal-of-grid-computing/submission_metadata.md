# Submission metadata

## Journal and article type

- Journal: Journal of Grid Computing
- Article type: Research Article
- Submission track: Regular issue
- Publishing route if accepted: Subscription publishing, no APC

## Title

Bounded Repair Reduces Cache Staleness under Lost Invalidation Messages: A Controlled Study across Web Applications

## Short title

Bounded Repair for Lost Cache Invalidations

## Abstract

Distributed application caches for mutable web data depend on update information that may arrive late or not at all. We evaluated eight cache policies in a controlled laboratory study spanning a mutable product service, an article feed and an administrative dashboard. The experiment used bounded synthetic request and update traces, page- or query-level responses, Redis Pub/Sub and Streams, and injected notification loss at 1%, 5% and 10%. The confirmatory campaign comprised 4,824 matched allocation blocks and 38,592 full policy executions, with 67 independent paired traces in each stratum. Across loss treatments, mean freshness-violation rates ranged from 0.119% to 7.755% with event-driven invalidation alone and from 0% to 0.388% with bounded repair. Relative to invalidation alone, repair reduced violations by 0.090 to 0.699 percentage points at 1% loss, 0.851 to 3.600 points at 5% loss and 1.478 to 7.654 points at 10% loss, while adding 6.6 to 131.2 microseconds to mean request wall time. Under reliable delivery, a write-reactive update-or-invalidate rule preserved the same freshness as fixed update and fixed invalidation, but reduced update traffic at the cost of higher request wall time relative to fixed update and showed workload-dependent CPU and origin-byte effects. These results identify bounded repair as an explicit reliability tradeoff and show that adaptive action selection moves cost between the request path, origin and notification channel without producing a universally superior policy.

## Keywords

1. application caching
2. cache invalidation
3. distributed systems
4. cache consistency
5. reliability
6. performance evaluation

## MSC 2020 classifications

- 68M14: Distributed systems
- 68M15: Reliability, testing and fault tolerance of networks and computer systems
- 68M20: Performance evaluation, queueing, and scheduling in the context of computer systems

## Authors

1. Vishwak Thatikonda
   - Affiliation: Independent Researcher
   - City, state, postal code and country: Dublin, California 94568, USA
   - Email: vishwakt@gmail.com
   - ORCID: 0009-0009-5828-5903
   - Contribution: Equal contribution
2. Shravani Parsi
   - Affiliation: Independent Researcher
   - City, state, postal code and country: Dublin, California 94568, USA
   - Email: shravaniparsi26@gmail.com
   - ORCID: 0009-0004-0084-4657
   - Corresponding author: Yes
   - Contribution: Equal contribution

## Portal declarations

- Funding: The authors did not receive support from any organization for the submitted work.
- Competing interests: The authors have no relevant financial or non-financial interests to disclose.
- Author contributions: Vishwak Thatikonda and Shravani Parsi contributed equally to the study and to preparation of the manuscript. Both authors read and approved the final manuscript.
- Ethics approval and consent to participate: Not applicable. This study did not involve human participants, human data or animals.
- Consent for publication: Not applicable.
- AI assistance: OpenAI ChatGPT through Codex assisted with code development and debugging.
- Prior or concurrent submission: None.
- Author approval: Both authors approved the submitted version.

## Data and code

- Dataset DOI: https://doi.org/10.5281/zenodo.23843162
- Raw archive release: https://github.com/shravaniparsi/Reinforcement-Learning-Framework/releases/tag/freshness-caching-study-v1.0.0
- Tagged code: https://github.com/shravaniparsi/Reinforcement-Learning-Framework/tree/freshness-caching-study-v1.0.0
