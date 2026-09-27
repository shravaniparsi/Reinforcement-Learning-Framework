# Contextual Rendering Selection Browser Study

This repository contains the software and numerical reproduction materials for the article "Contextual Rendering Selection Beyond Strong Fixed Baselines: A Controlled Browser Study."

The final study compares server-side rendering and client-side rendering in three web application workflows. It evaluates six frozen policies using matched browser observations from a 12-session Mac cohort and a separate 12-allocation hosted Linux cohort. Each cohort contains 864 action observations. The contextual lookup table improved the cohort mean by 0.239 ms on the Mac and by a descriptive 0.302 ms on hosted Linux relative to a training-selected fixed policy. These small differences do not establish practical deployment benefit or reinforcement-learning superiority.

## Reproduce the reported scores

The self-contained numerical package is in `reproducibility/final-study`.

```sh
cd reproducibility/final-study
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python reproduce_scores.py
```

The script verifies file hashes, schedule completeness, correctness gates and cell balance. It then reproduces the six frozen-policy means for each cohort and the original Mac conditional bootstrap interval. It does not start browsers, recollect observations or refit policies.

## Evidence boundaries

- Mac and hosted Linux observations are analyzed as separate cohorts.
- The primary endpoint is navigation-to-application-marker time. It is not a visual-completion or user-interaction metric.
- The cloud cohort is descriptive because fresh hosted allocations do not establish independent physical hosts.
- The package reproduces final frozen-policy scoring. It does not reproduce the complete development, fitting or pilot history.
- Historical simulator and PPO materials elsewhere in the repository are not evidence for the final browser-study conclusions.

See `reproducibility/final-study/README.md` for provenance, expected values and package limitations.

## Citation and archival release

Citation metadata is provided in `CITATION.cff` and `.zenodo.json`. Version 1.0.0 is being prepared for archival through GitHub and Zenodo. The journal article DOI will be added as a related identifier after it is assigned.

## Licensing

The authors' original software is available under the MIT License. The authors' original research data and documentation are available under CC BY 4.0. Third-party components retain their own licenses. See `LICENSE_SCOPE.md` for the file-level boundary and retained upstream notice.
