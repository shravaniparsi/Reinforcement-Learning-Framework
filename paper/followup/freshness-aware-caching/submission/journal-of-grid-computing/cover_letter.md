31 October 2026

Editors-in-Chief
Journal of Grid Computing

Dear Editors-in-Chief,

Please consider our Research Article, "Bounded Repair Controls Cache Staleness under Lost Invalidation Messages: A Controlled Study across Web Applications," for publication in the Journal of Grid Computing.

The manuscript reports a controlled experimental study of reliability and performance tradeoffs in distributed application caches. Across three mutable web applications, two Redis delivery modes and matched notification-fault schedules, we compare eight established cache policies using complete-content freshness oracles. The confirmatory campaign contains 4,824 matched allocation blocks and 38,592 full policy executions. The results show that bounded repair consistently recovers freshness lost after missing invalidation messages, with measurable request-time and CPU costs. They also show that write-reactive selection shifts work between the request path, origin and notification channel without universally dominating fixed update or invalidation.

We believe the paper fits the journal's emphasis on dependable distributed systems, distributed data management, and experimental performance evaluation. Its practical contribution is a reproducible evaluation method and a measured reliability tradeoff for application caches operating over imperfect notification delivery. The study reports freshness, latency, CPU, origin traffic and messaging traffic separately rather than combining them in a subjective utility score.

The manuscript is original, has not been published, and is not under consideration elsewhere. Both authors approved the submitted version. Neither author has a competing financial or non-financial interest, and the work received no funding or other organizational support. The study did not involve human participants, human data or animals.

Analysis-ready results and the reproducibility package are archived at Zenodo (https://doi.org/10.5281/zenodo.23843162). All 4,824 raw execution archives and the tagged study code are also publicly available through the linked GitHub release.

Thank you for considering our manuscript.

Sincerely,

Shravani Parsi
Corresponding author
Independent Researcher
Dublin, California 94568, USA
shravaniparsi26@gmail.com
ORCID: 0009-0004-0084-4657
