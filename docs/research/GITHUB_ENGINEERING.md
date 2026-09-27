# GitHub-hosted Linux browser engineering

This is a manually triggered, engineering-only portability check. It does not train RL, collect a new test cohort, estimate policy gains or change the completed Mac study. Standard public-repository Ubuntu runners are used; private repositories are skipped, with no paid fallback.

The `Linux Browser Engineering` reusable/manual workflow is also reachable through the existing `Run RL Experiments` dispatcher by selecting `mode=engineering`. This bridge permits explicit dispatch on a feature branch before the new workflow exists on the default branch. Other modes retain the legacy simulator behavior and are not part of this check.

## Pinned inputs

- Ubuntu 24.04 x64 hosted runner label. The image revision/CPU are recorded, not assumed constant.
- Node 20.19.6, Python 3.9.25, pnpm 10.20.0; root npm and patched external pnpm lockfiles.
- Browser-only Python requirements in `experiments/ci_engineering/requirements.lock.txt`.
- Chrome for Testing 154.0.8037.57 Linux64 archive with SHA-256 `ceee2972074d441ea7c4ba8bcc0eaab77e7e87680f6653d73d3065851fe10302`, checked against the official download on 26 September 2026.
- Svelte RealWorld upstream commit `df796708040f5200ec572b28ab7f88ecee5794dd`, the existing production adaptation patch and buffered-data adapter installed as a same-origin startup asset in both variants.
- GitHub action implementations pinned by commit SHA. Browser OS libraries are installed from the runner's package repositories; this does not pin every OS package or claim bitwise build reproduction.

## Execution

After the branch has been published, dispatch `experiments.yml` explicitly against that branch with mode `engineering`. No cron, push trigger, pull-request trigger or automatic retry is defined. Branch code must be reviewed before dispatch because the workflow executes it.

The job installs dependencies, verifies the Chrome archive, exercises failure-gate unit tests and rebuilds fresh production Next and Svelte variants. All five application/API processes bind to loopback and are owned/stopped by the runner. It verifies initial HTML treatments, expected content, selected interactions, request failures, external requests and the actual served adapter bytes. It executes the existing 72-observation engineering matrix with unthrottled loopback networking. It does not repeat the prior eight network-stress cases; this pass does not establish network-emulation reliability.

## Outputs and pass criteria

Each attempt gets a distinct artifact, retained for 14 days, containing build logs, build/source identities, allowlisted runner metadata, CPU/memory records, browser identity, functional preflight records, engineering JSONL, traces and checksums. The job uses read-only repository permissions and does not upload a dump of environment variables or credentials. Workflow setup failures remain in GitHub logs; failures before output creation may have no artifact.

A pass requires all 72 scheduled observations, matched content, no recorded browser/nonlocal-request failures, valid timing, successful adapter checks and unchanged production build fingerprints during the check. A failed or partial matrix is retained and fails the job. Results remain marked `eligible_for_main_study: false`, including when checks pass. Save successful/failed artifacts locally before their GitHub retention expires.

There is no study-collection CLI option in this new entry point. It refuses local/self-hosted execution and existing builds so it cannot replace the locked local experiment. Fresh runner allocations are not proof of independent physical hardware; any subsequent hosted-runner study must define its own sampling/inference protocol and report infrastructure limitations.

## After engineering passes

Inspect the artifact and resolve portability failures first. Then specify the separate replication's sample size, allocation/blocking, frozen policy inputs, failure rules and analysis before collecting its observations. The engineering timings are excluded from that future cohort. No additional daily run is implicitly scheduled.
