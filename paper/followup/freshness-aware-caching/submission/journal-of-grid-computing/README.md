# Journal of Grid Computing submission package

This directory contains the venue-adapted package for a regular Research Article submission to the Journal of Grid Computing.

## Files

- `upload/manuscript.tex`: submission source in the official Springer Nature LaTeX format
- `upload/references.bib`: verified bibliography plus the Zenodo dataset citation
- `upload/Fig1.pdf` and `upload/Fig2.pdf`: final vector figures
- `upload/Supplementary_Data_S1.csv`: descriptive summaries for all eight policies and five outcomes
- `upload/Supplementary_Data_S2.csv`: post hoc familywise repair-freshness sensitivity
- `upload/sn-jnl.cls` and `upload/sn-mathphys-num.bst`: official Springer Nature template files, December 2024 version
- `cover_letter.md`: journal-specific cover letter
- `submission_metadata.md`: exact portal metadata and declarations
- `SUBMISSION_CHECKLIST.md`: final preflight and portal checklist
- `journal-of-grid-computing-manuscript.pdf`: final compiled review manuscript
- `journal-of-grid-computing-latex-source.zip`: flat SNAPP source archive, verified by compilation from a fresh extraction

## Build

From the `upload` directory, run:

```sh
latexmk -pdf -interaction=nonstopmode -halt-on-error manuscript.tex
```

The SNAPP manuscript upload must be a flat ZIP whose files are all at the archive root. The two Supplementary Data files should also be uploaded as supplementary material in the portal.

## Author affiliation

Both authors are listed as Independent Researchers in Dublin, California 94568, USA.
