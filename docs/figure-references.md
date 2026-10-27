# Figure-reference display style

The Gallery uses a compact citation style in both cards and detail metadata:

- `Fig. 1` for an entire figure; no `complete`, `all`, or `Full figure` suffix.
- `Fig. 1a` and `Fig. 1a–c` for labelled panels.
- `Fig. 1A–C` when the published paper uses uppercase panel letters.
- `Fig. 3a,c,e` for nonconsecutive panels; never turn a selection into a continuous range.
- A space follows `Fig.`; panel letters follow the number without a space.
- Library descriptors such as `maps`, `profiles`, or positional excerpt names are omitted from the citation. Excerpt/alteration information remains in the rights details.

`GalleryTools.formatFigureReference` formats display strings without mutating imported or approved metadata, image bytes, permission decisions, or hashes. Unrecognized reference structures are preserved rather than guessed. Original and formatted references remain searchable. Supplementary and Extended Data references are not silently converted into main-text figures.

## Panel case: evidence before defaults

Do not apply lowercase/uppercase to an entire publisher family. Prefer the formal published PDF and the actual panel labels. For an Article in Press version, check the journal's final style if normalization is needed; never replace an approved image version through a display cleanup.

The 2026-10-26 review read the local PDFs for all 78 papers represented by the 464 public records. Three papers with uppercase source references were specifically checked visually: Nature Communications 10.1038/s41467-025-63600-1 (p. 3), Nature Communications 10.1038/s41467-026-72549-8 (p. 2), and PNAS 10.1073/pnas.2616535123 (p. 2). Their uppercase letters are intentional. No Science-family paper was present in this public dataset.

Official references:

- [Nature final-submission guidance](https://www.nature.com/nature/for-authors/final-submission) generally specifies lowercase multipart labels.
- [Nature author style checklist](https://mtscommon.nature.com/letters/author_style_checklist.pdf) provides compact citation examples such as `Fig. 1a` and `Fig. 2a–d`.
- [PNAS manuscript guidance](https://www.pnas.org/author-center/submitting-your-manuscript) is a reference for future submissions; actual published panel case still takes priority.
- [Science manuscript guidance](https://www.science.org/content/page/instructions-preparing-initial-manuscript) could not be independently read during this review (access blocked). No unverified Science-specific case conversion is implemented.

Private per-paper PDF paths, hashes and before/after display comparisons stay under the website's ignored `.gallery-local/figure-reference-review-20261026/` directory. They are not needed by production builds.
