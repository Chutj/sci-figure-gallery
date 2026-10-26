# Contributing

Thank you for helping improve SCI Figure Gallery.

## Suggest a figure

Use the figure-suggestion issue template. The paper title and figure/panel number
are required. You can enter `All` to recommend all figures in a paper. Examples
include `Figure 1`, `Figure 2b`, and `Figure 3a–c`.

A DOI or article link, your reasons for recommending the figure, and any license
or credit information are optional. There is no need to research the license
before making a suggestion.

**Please provide references first.** To help us respect copyright, paper PDFs and
image files are not needed at this stage. Maintainers will review the suggestion,
check the applicable permissions, and add the figure files when permitted.
Public issue and PR attachments are accessible immediately, so references are
the preferred way to share a suggestion.

Only maintainers may finalize publication approval after human review. Do not set
`human_reviewed`, `public_use_allowed` or `status: approved` on the strength of an
article's open-access label, an AI answer or another figure from the same paper.

## Improve the code or public descriptions

1. Fork this repository and create a branch.
2. Make a focused change. Preserve the original image proportions, accessibility,
   English interface and individual source/license information.
3. Run `python -m unittest discover -s scripts -p "test_*.py"` and
   `python scripts/validate_public_gallery.py`.
4. For UI changes, check desktop and mobile widths with the local preview.
5. Open a PR describing the change and its validation.

Please edit Gallery code here, not the academic website's managed copies. A change
is released to the live site only after a maintainer deliberately updates the
website's pinned component version and deploys it.

Contributions to project-owned code and documentation are made under the project's
MIT license. Contributing does not change the license of any research figure or
grant rights in someone else's material.

## Figure review checklist

- Match the DOI and the actual paper version, including Article in Press status.
- Identify the exact complete figure or panel and retain its original source.
- Verify the applicable article license and figure-specific exceptions/credit lines.
- Check whether the actual use is noncommercial when NC applies.
- Review any extraction or modification against ND/SA and other applicable terms.
- Supply complete attribution, DOI/source, license link and modification notice.
- Pin the exact image, metadata and permission-evidence fingerprints.
- Keep raw PDFs and private supporting evidence out of the public repository.

CI verifies structure and pinned bytes. It does not issue a legal permission or
replace the maintainer's human decision.
