# Journal of Grid Computing submission package

This directory contains the venue-adapted package for a regular Research Article submission to the Journal of Grid Computing.

## Files

- `upload/manuscript.tex`: submission source in the official Springer Nature LaTeX format
- `upload/references.bib`: verified bibliography plus the Zenodo dataset citation
- `upload/Fig1.pdf` and `upload/Fig2.pdf`: final vector figures
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

The SNAPP upload must be a flat ZIP whose files are all at the archive root. The package must compile with `pdflatex`.

## Author affiliation

Both authors are listed as Independent Researchers in Dublin, California 94568, USA.
