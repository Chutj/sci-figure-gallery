# SCI Figure Gallery

Scientific figures for academic learning and scientific visualization reference.

**[Explore the interactive gallery](https://chutj.github.io/gallery/)**

This repository maintains the public Gallery component used by Chutj's academic
website. The live gallery remains at the existing address; this repository does
not deploy a second website or replace the academic site's Home and GEE Access.

The initial release contains **31 reviewed figures from 7 papers**: one CC BY 4.0
figure and 30 CC BY-NC-ND 4.0 figures. These are individual reviewed image files,
not a blanket approval of every figure in those papers.

## Browse and learn

- Responsive three-column masonry layout, with two columns on smaller screens.
- Category browsing, keyword search, sorting and collapsible field-specific filters.
- Large-image details, zoom controls, source citations and individual licenses.
- Copyable HEX swatches; image-sampled colors are explicitly approximate.
- Notes on figure content, statistical symbols, color encoding and design ideas.

## Contribute

Suggestions, corrections, accessibility improvements and code contributions are
welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md).

For a new figure, open a **figure suggestion** with the paper DOI, official source,
figure/panel number and what makes the visualization useful. Please do not upload
paper PDFs, unreviewed images, private metadata or personal credentials to an issue
or pull request. Public submissions are already public before a PR is merged.

Maintainers review the exact image version, third-party credits, permissions,
attribution and modification status before admitting any public figure. A shared
article license, an AI assessment or a passing CI check does not replace that review.

## Run locally

Requirements: Git, Python 3.11+, Hugo Extended 0.168.0, and Node.js 20+ for frontend
helper tests. The public build has no Python package dependencies and needs no
account secrets, FIG library or original PDFs.

```sh
git clone --recurse-submodules https://github.com/Chutj/sci-figure-gallery.git
cd sci-figure-gallery
python scripts/validate_public_gallery.py
python -m unittest discover -s scripts -p "test_*.py"
python scripts/serve_preview.py
```

The preview is available at `http://127.0.0.1:1320/gallery/`. It validates a clean
production build first, then rewrites only its disposable local HTML to use the
same reviewed image bytes locally. The tracked public dataset and approvals stay
unchanged. If Hugo is outside PATH, use `--hugo /path/to/hugo`.

For a production check:

```sh
hugo build --environment production --minify
python scripts/validate_public_gallery.py --output public
```

## Structure

| Path | Purpose |
| --- | --- |
| `assets/`, `layouts/` | Gallery UI and Hugo/PaperMod templates |
| `data/gallery/public.json` | Reviewed public metadata |
| `data/gallery/allowlist.json` | Explicit approvals with version and evidence pins |
| `data/gallery/media.json` | Exact image and thumbnail hashes |
| `static/figures/approved/` | Only the approved image versions |
| `gallery-component.json` | Explicit files shared with the academic website |
| `scripts/` | Validation, tests, preview and pinned website synchronization |
| `PROVENANCE.json` | Original website commit and imported-file hashes |

## Website integration

The independent repository is the maintenance source for the public Gallery.
The website keeps a version-pinned, hash-checked copy so its existing Hugo build
remains self-contained and its `/gallery/` address stays stable.

```sh
python scripts/sync_website.py plan --website ../chutj.github.io
python scripts/sync_website.py apply --website ../chutj.github.io
```

Only a committed component version can be synced. The website records the exact
commit and every managed file hash in `gallery-component.lock.json`; its existing
production validation rejects drift. A community PR or new upstream commit does
not automatically update the live site. Review and deploy the website separately.

The owner's FIG import, PDF association and private rights evidence remain outside
this repository. See [the maintainer workflow](docs/maintainers.zh-CN.md).

## Licensing

Project-owned software and project documentation use the **MIT License**. Research
figures and other third-party material are excluded from MIT and retain their
individual terms. In particular, CC BY-NC-ND images are not available for unrestricted
commercial reuse or distribution of adaptations.

Read [LICENSE](LICENSE), [LICENSES.md](LICENSES.md) and each figure's attribution,
license link and modification notice. No single Creative Commons license is
applied to the entire collection. Rights questions: [chutj@foxmail.com](mailto:chutj@foxmail.com).

The original website history is preserved. This project's initial extraction is
documented in `PROVENANCE.json`; PaperMod remains a separately pinned submodule
with its own license. Private FIG materials and original papers are not included.
