# Clustered-loss final protocol v1

## Status

Both authors approved the 84-seed design on 5 November 2026. This document prospectively authorizes final data collection only after the workflow, analyzer, tests, and exact source commit are frozen. The completed precision-planning observations remain separate from the future final sample and will not be reused as final observations.

## Planning result and sample-size decision

The frozen precision analysis evaluated candidate final sample sizes of 12, 18, 24, 30, 36, and 48 independent trace seeds. No candidate satisfied every prespecified rule. The nonzero planning-variance estimates required at least 73 seeds for the freshness interaction target and 67 seeds for the persistence interaction target. The repair-only persistence contrast had zero observed planning variance, so the original analyzer correctly declined to assign it a width of zero.

The revised rule uses the largest stable 90% upper standard-deviation bound within each endpoint family. This gives variance envelopes of 0.021403538900218184 for freshness estimands and 0.20435953592760125 for persistence-at-10 estimands. With individual 95% intervals, 84 fresh seeds project full widths of 0.009289705366527224 and 0.08869747598553893, respectively. Both fall within the original targets of 0.01 and 0.10. The count of 84 is the 73-seed minimum plus a 15% buffer, rounded up.

The intervals are individual estimation intervals. The study will not make a simultaneous familywise-coverage claim or use binary significance testing across the four estimands.

## Independent unit and fixed design

The independent unit is the trace seed. Each seed crosses three applications, three workload regimes, and two Redis transports, giving 18 fixed strata per seed. The matched fault-profile contrast remains single-burst-10 minus dispersed-10. The primary policy remains event-invalidate-with-repair, and the interaction reference remains always-invalidate. The workload definitions, fault schedules, policies, locked parameters, outcome definitions, recovery horizon, and counterbalancing rules remain unchanged.

Final seeds will be 2200 through 2283. Precision-planning seeds 2100 through 2109 will not enter the final estimates.

## Collection and analysis controls

GitHub limits a workflow matrix to 256 jobs. The 1,512 final jobs will therefore be divided into six shards of 14 seeds. Each shard contains 252 jobs and covers the complete 3 by 3 by 2 factorial for its seed range. All six shards must pass archive-digest, ZIP-CRC, factorial-coverage, manifest, protocol, lock-hash, schedule-hash, and result-completeness checks before the final analysis is opened.

There will be no interim effect analysis, sample-size reassessment, early stopping, or reuse of planning observations. The final analyzer and collection workflow must be frozen and tested before collection is authorized.

## Execution gate

The 84-seed design and its expected 1,512-job collection cost are authorized. Before any final workflow is launched, the exact source commit and protocol digest must be recorded, all contract tests must pass, and the workflow must be dispatched only from that frozen source commit.
