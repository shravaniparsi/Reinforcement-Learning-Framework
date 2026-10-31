# Cache-freshness confirmatory data release

Release version: 1.0.0

This release supports the manuscript **“Bounded Repair Controls Cache
Staleness under Lost Invalidation Messages: A Controlled Study across Web
Applications.”** It is a separate dataset deposit from the repository's earlier
contextual-rendering study.

## Release assets

`freshness-caching-study-v1.0.0-core.zip` contains:

- the checksum-bound confirmatory analysis JSON;
- all 450 paired primary estimates in CSV form;
- contrast-level summary data;
- source data and rendered files for Figures 1 and 2;
- protocol v0.5 and the machine-readable final design;
- the frozen confirmatory analyzer and reporting script;
- the archive inventory, data dictionary and file manifest; and
- the repository commit from which the package was built.

`freshness-caching-study-v1.0.0-raw-archives.tar` contains all 4,824
GitHub Actions artifact ZIP files without recompression or modification. Each
artifact represents one matched allocation block and contains eight complete
policy executions. Checksums for the individual artifacts are recorded in the
archive inventory inside the core package.

`CHECKSUMS.sha256` authenticates both release assets.

## Evidence population

The confirmatory campaign contains 4,824 matched allocation blocks and 38,592
complete policy executions. It spans three workloads, three request/update
regimes, four primary fault conditions, two Redis transports and 67 final-test
seeds. Every primary estimate uses 67 complete paired traces.

## Reproduction routes

The analysis-ready estimates and figures can be inspected directly from the
core package. Re-running the frozen confirmatory analyzer requires the raw
archive bundle and the source repository at the commit recorded in
`repository_commit.txt`. The repository includes the training parameter files,
held-out validation record, sample-size lock and analyzer dependencies.

## Access and licensing

The authors' original data and documentation are licensed under CC BY 4.0.
Original software is licensed under MIT. The release does not redistribute
third-party application source; the source repository identifies pinned
upstream commits and retains their original notices.

## Citation

Use the DOI assigned to the independent Zenodo dataset record. Until that DOI
exists, cite the versioned GitHub release and repository commit recorded in the
package. Do not use the earlier contextual-rendering dataset DOI for this study.
