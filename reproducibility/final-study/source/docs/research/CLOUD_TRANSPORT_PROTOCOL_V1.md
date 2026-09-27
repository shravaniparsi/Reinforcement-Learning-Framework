# Prospective frozen-policy cloud transport protocol v1

26 September 2026 Pacific time. Defined after engineering run 36294072895, before any eligible cloud transport observation. Engineering outcomes are excluded and their policy contrasts have not been used for planning. This protocol supersedes the sampling decisions left open in the design brief; it does not amend the completed Mac study.

**Question:** What descriptive context-table minus per-application fixed-policy endpoint contrast is observed when the original fitted policies are transported to fresh GitHub-hosted Ubuntu allocations?

## Cohort and resource budget

Collect exactly 12 fresh job allocations within one manually launched GitHub workflow, at most one allocation job running at once. Each builds from the same immutable Git commit. There are 72 observations per allocation: three applications × two CPU emulation rates (1, 4) × two cache states × three cases/repetitions × two actions (SSR, CSR), or 864 observations and 432 matched pairs overall. Case definitions and measurement implementation are reused unchanged. Catalog cases are repetitions of one workload. Pair order and within-pair action order are deterministically randomized by a new allocation-specific seed before collection.

Twelve is a fixed resource budget, chosen to obtain repeated hosted-allocation descriptions at the same observation count as the original test cohort. It is not a power calculation, achieved precision guarantee, or reuse of the original 5 ms planning rule. There is no optional extension based on effect direction or magnitude. No calendar-day spacing is imposed; record actual start/end dates and group descriptive results by UTC start date. Queue order need not equal allocation index.

An allocation is the descriptive aggregation unit. Fresh VMs do not establish independent physical computers, independent noise, or broad hardware coverage. Shared infrastructure, job image updates, burstable load and calendar dependence remain possible. No confidence interval, p-value, independence claim, or population-generalization inference will be made from this cohort. A separate prospective multi-day or hardware-controlled study would be needed for stronger inference.

## Frozen software and policies

Use Ubuntu 24.04 standard public-repository hosted runners, Node 20.19.6, Python 3.9.25, pnpm 10.20.0, the existing locked dependencies and Chrome for Testing 154.0.8037.57. Verify the Linux browser archive SHA-256 `ceee2972074d441ea7c4ba8bcc0eaab77e7e87680f6653d73d3065851fe10302`. Record VM CPU/memory, OS/image, package versions, browser executable digest, build fingerprints, Git SHA and workflow identity per allocation. The hosted image itself is not immutable; report any variation rather than filtering allocations by hardware or image after collection.

The original frozen-policy payload SHA-256 is `8b7ac71519fb3f7db4d1a6be2df337410c24d5e1c8d1cff5d8e96a82ee7ad9e2`. Export its exact actions for all 12 supported contexts and all six policies using the original verified implementation. No new fitting, penalty selection, action threshold, feature estimation or use of cloud outcomes is allowed. A finite-domain action export is sufficient because all evaluated contexts were predefined. Retain the original local artifact and implementation; publish the export without the artifact's local filesystem provenance paths.

Use the application-integrated buffered adapter for both external actions, the same upstream Svelte commit and patch as the successful engineering run, unthrottled loopback networking, and unchanged endpoint/correctness checks. Preflight initial HTML and six warmups are diagnostics, excluded from analysis. The mount/hydration endpoint is not paint, interactivity, user experience, or end-to-end deployed policy latency. Context labels are supplied by the experiment; both action outcomes are observed offline.

## Prospective lock, failure and stopping rules

Publish this protocol, action map, collector, analysis, tests, workflow and all reused runtime sources under a SHA-256 file lock before collection. Verify that lock before and after measurement. Use a single workflow run ID and attempt 1 for the cohort; all 12 allocations must share its commit and lock. Engineering, previous Mac and other workflow runs are ineligible. The lock is prospective version control, not independent registry registration.

A job failure stops queued work through the workflow's fail-fast behavior. Retain all logs, partial observations and failure receipts. Do not rerun a failed job, substitute an allocation, remove outliers, drop failed observations, or combine partial workflow attempts. All 12 complete valid allocations are required before computing policy contrasts. Infrastructure/setup failure also makes the planned cohort incomplete. Diagnose failures without reviewing policy contrasts; any necessary retry requires a documented prospective amendment and a new complete cohort with the abandoned run retained. No blind automatic retry of the cohort is authorized by this protocol.

Browser errors, nonlocal requests, missing/wrong content, invalid endpoint values, schedule mismatch, missing adapter checks, changed build bytes or source-lock mismatch fail the completeness gate. Download artifacts before their 30-day expiry, verify all hashes and retain them locally. Analysis performs no measurements and refuses incomplete/mixed cohorts.

## Analysis and interpretation

For each allocation and each of the 12 application × CPU × cache cells, average its three endpoint observations separately for SSR and CSR. Each frozen policy's allocation score is the equally weighted mean of its 12 selected cell/action means. The primary descriptive contrast is context-table score minus best-fixed score, in milliseconds (negative favors the context table). Average allocation scores equally over all 12 allocations. Report all six policy means, every allocation contrast, contrast mean/median/minimum/maximum and negative/zero/positive counts. Relative reduction is 100 × (mean fixed − mean context) / mean fixed, undefined if mean fixed is zero.

Report every cell's two action means and context-versus-fixed difference, including cells where policies agree. Report date-level means and counts as descriptive summaries only. Do not treat individual observations, repeated cases or same-day allocations as independent replications. Keep this cohort separate from the Mac results; show comparisons side by side without pooled estimates or significance testing.

A negative cohort mean is descriptive directional agreement; a positive mean is descriptive directional reversal; an exact zero is no mean difference. Mixed allocation signs are explicitly reported as instability. None establishes statistically reliable transport or practical user benefit. An incomplete cohort has no aggregate policy result. Publish reversal or weak/mixed results with the same prominence as agreement. This addition can address environment transfer only; it does not by itself resolve the manuscript's small-effect/practical-significance limitation or guarantee journal suitability.
