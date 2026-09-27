# Numerical reproduction package

This package preserves the 24 final test units (1,728 original observation records) and the exact finite-context actions of all six frozen policies. Mac and cloud cohorts remain separate. The source directory contains the prospectively locked cloud code, fixtures and dependencies; its lock is unchanged. See `DATA_DICTIONARY.md` for field definitions.

## Reproduce the reported scores offline

From this candidate directory, create a Python 3.9 environment, install `requirements.txt`, then run:

```sh
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python reproduce_scores.py
```

The script verifies the inventory, complete schedules, correctness/content/error gates and every cell's three observations, then recomputes all six policy means and the context-minus-fixed contrasts. It also reproduces the original Mac whole-session conditional bootstrap interval with NumPy 2.0.2 and seed 20260918. Cloud results remain descriptive. No browser, new measurement, training or token is required for score reproduction. Installing dependencies requires network access unless they are already cached.

Expected rounded contrasts: Mac −0.239 ms; cloud −0.302 ms. Mac conditional interval: [−0.399, −0.092] ms. Cloud allocation signs: eight negative, four positive. These are small lifecycle-timing differences, not measured user benefit.

## Provenance and limits

Raw JSONL observation bytes are unchanged and checked against the original analyzed cohort hashes. `units.json` files are explicitly derived metadata extracts; they retain complete schedules, browser/start identities and the original manifest hashes without exposing complete host/activity logs. `expected-results.json` is a derived numerical extract, not a replacement for the original report envelopes. The original manifests, failed/engineering attempts, training/validation/variance data, traces and reports remain retained in the research workspace.

This package reproduces the **final frozen-policy scores**, not the entire fitting history or every pilot figure. It does not claim a complete independent reproduction or supply all historical evidence. A pattern scan found no specified local-home, key or token patterns, but this is not a guarantee that every identifying or sensitive string has been detected.

For the already-executed cloud collection, the source snapshot corresponds to Git commit `2649b732bbcf49306fd5fedfa5d0f7a6271b70b3` and run 36294734822. Executing new browser experiments is a separate operation requiring the documented environment and a new study identity; the reproduction command above does not start them. The compact `source/` snapshot is not a Git checkout and should not be used directly as a new collection workspace.

## Licensing

The authors' original software is licensed under MIT. The authors' original research data and documentation are licensed under CC BY 4.0. Third-party materials retain their own licenses. See the repository-level `LICENSE`, `DATA_LICENSE.md` and `LICENSE_SCOPE.md` files.
