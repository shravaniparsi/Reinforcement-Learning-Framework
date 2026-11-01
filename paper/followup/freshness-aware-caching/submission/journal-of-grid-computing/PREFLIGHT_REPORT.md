# Journal-specific preflight report

Date: 31 October 2026

## Readiness assessment

The package is scientifically and technically ready for submission to the *Journal of Grid Computing*.

## Remaining editorial risk

No submission-blocking defect remains. The principal irreducible risk is venue fit: the paper evaluates reliability and performance in distributed application caches, but its web-application setting is narrower than some infrastructure-focused work published by the journal. The title, abstract, Introduction and cover letter consistently present the distributed-systems contribution without expanding the claims beyond the controlled study.

## Completed scientific checks

- All 4,824 allocation blocks and 38,592 policy executions were read from the frozen release archive.
- The archive SHA-256 is `598be5e50c7644e9acc2ec5b32438d0460f3d40b4419bb9d958323037dd6e590`.
- All 450 released primary estimates were reproduced exactly.
- Online Resource 1 contains 2,880 descriptive policy-outcome summaries: 72 strata, eight policies and five outcomes.
- Online Resource 2 contains all 54 repair-freshness estimands and the post hoc simultaneous one-sided 95% familywise sensitivity bounds.
- The Online Resource files preserve every scientific data field exactly and include the article, journal, author, corresponding-author and affiliation metadata required for supplementary files.
- The absolute freshness-rate ranges, paired reductions, sample-size calculation, admissibility gate and write-reactive decision rule were checked against the analysis outputs and protocol.
- The complete freshness test suite passes: 105 tests run, zero failures or errors.

## Completed citation and claim checks

- Fifteen unique citation keys are used and all resolve to fifteen unique bibliography entries.
- No cited key is missing, no bibliography entry is uncited, and no duplicate key or DOI is present.
- The submission bibliography matches the verified source ledger, with the cited Zenodo record added for the study dataset.
- The Gray and Cheriton leases paper and the Nishtala et al. production Memcache paper were added to place bounded authority and missed-invalidation recovery in context.
- The description of Mao et al. follows the cost derivation and records the conflicting action labels in the source rather than silently reproducing them.
- No citation placeholders or unresolved cross-references remain.

## Completed manuscript and package checks

- Official Springer Nature `sn-jnl` LaTeX template and numeric mathematics/physics bibliography style retained.
- Clean `pdflatex` and BibTeX build completed with no undefined citations or references, overfull boxes or LaTeX errors.
- Final PDF: 14 A4 pages; every page was visually inspected.
- Table 1, both equations, Figures 1 and 2, declarations and the complete reference list render without clipping or overlap.
- Figure-internal titles were removed in accordance with the journal artwork instructions; the captions remain in the manuscript, marker shapes supplement color, and all vector fonts are embedded.
- The embedded PDF title, author and keyword metadata match the submission metadata.
- Abstract length: 228 words, within the journal's 150-to-250-word range.
- Six keywords and three MSC 2020 codes are present.
- Title, abstract, portal metadata, cover letter and Markdown manuscript use the same claim and title.
- The independent source archive contains exactly six files (`manuscript.tex`, `references.bib`, `Fig1.pdf`, `Fig2.pdf`, `sn-jnl.cls`, and `sn-mathphys-num.bst`) and compiles successfully after fresh extraction.
- Online Resources 1 and 2 are separate upload files and are not embedded in the LaTeX source ZIP.
- The current journal instructions were rechecked on 31 October 2026: the abstract, keyword count, MSC codes, LaTeX source, declarations, AI disclosure, data statement and Online Resource naming conform to the stated requirements.
- The Zenodo DOI resolves to an open record with both authors and both ORCIDs; the tagged GitHub release and code tag return publicly accessible pages.
- Funding, competing interests, ethics, consent, data availability, code availability and equal-author-contribution statements are present.
- AI assistance is disclosed in Methods using the author-approved limited statement.
- No em dashes appear in the manuscript, cover letter or portal metadata.

## Submission action

Upload the final manuscript PDF, the six-file LaTeX source ZIP, Online Resource 1, Online Resource 2 and the cover letter. Inspect the portal-generated review PDF before approving the submission.
