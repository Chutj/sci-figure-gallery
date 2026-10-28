# SCI Figure Gallery

Scientific figures for academic learning and scientific visualization reference.<br>
用于学术学习与科学可视化参考的科研图件库。

**[Explore the interactive gallery](https://chutj.github.io/gallery/)**<br>
点击上方链接，访问可交互图库。

This repository provides the gallery component for the academic website.<br>
本仓库为个人学术网站的 Figure Gallery 提供代码和公开图件。

As of **2026-10-28**, the gallery contains **1,523 reviewed figures from 238 papers**: 1,029 from CC BY 4.0 articles, 241 from CC BY-NC 4.0 articles, and 253 from CC BY-NC-ND 4.0 articles. Figure-specific credits and additional terms accompany each figure.<br>
截至 **2026-10-28**，图库收录来自 **238 篇论文的 1,523 张已审核图件**：1,029 张来自 CC BY 4.0 论文，241 张来自 CC BY-NC 4.0 论文，253 张来自 CC BY-NC-ND 4.0 论文。逐图保留必要署名和附加条款。

## Browse and learn / 浏览与学习

- Three-column masonry layout, with two columns on smaller screens.<br>
  瀑布流布局，桌面显示三列，较小屏幕显示两列。
- Figure-type and learning-focus filters, keyword search, advanced search and sorting.<br>
  按图件类型和学习关注点筛选，支持关键词搜索、高级检索及排序。
- Large-image details, zoom, source citations and individual licenses.<br>
  查看大图与详细说明，支持缩放，并提供来源和逐图许可证。
- Copy the figure’s main colors as HEX values.<br>
  点击色块，复制图中多个主要颜色的 HEX 色值。
- Notes on figure content, statistical symbols, color encoding and design ideas.<br>
  学习图件内容、统计符号、颜色编码及设计思路。
- Classified source excerpts, with shared legends displayed separately.<br>
  保留按类别整理的原始摘录；共享图例单独展开，不拼接不同图型的面板。

## Contribute / 参与共建

Suggestions, corrections, accessibility improvements and code contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).<br>
欢迎提出建议、纠正信息、改善无障碍体验或贡献代码。参与方式见 [CONTRIBUTING.md](CONTRIBUTING.md)。

To recommend a figure, use the **[figure suggestion form](https://github.com/Chutj/sci-figure-gallery/issues/new?template=figure-suggestion.yml)**.<br>
如想推荐图片，可直接填写 **[图片建议表单](https://github.com/Chutj/sci-figure-gallery/issues/new?template=figure-suggestion.yml)**。

## Run locally

Requirements: Git, Python 3.11+, Hugo Extended 0.168.0, and Node.js 20+ for frontend tests. No private FIG materials, PDFs or account secrets are required.

```sh
git clone --recurse-submodules https://github.com/Chutj/sci-figure-gallery.git
cd sci-figure-gallery
python scripts/validate_public_gallery.py
python -m unittest discover -s scripts -p "test_*.py"
python scripts/serve_preview.py
```

Open `http://127.0.0.1:1320/gallery/`. The preview validates the public build and uses local image URLs without changing approved data. Use `--hugo /path/to/hugo` if Hugo is outside PATH.

Production check:

```sh
hugo build --environment production --minify
python scripts/validate_public_gallery.py --output public
```

## Structure

| Path | Purpose |
| --- | --- |
| `assets/`, `layouts/` | Gallery UI and templates |
| `data/gallery/` | Public metadata, approvals and media hashes |
| `static/figures/approved/` | Approved images and thumbnails |
| `gallery-component.json` | Files shared with the academic website |
| `scripts/` | Validation, tests, preview and synchronization |
| `PROVENANCE.json` | Source history and import hashes |

## Website integration

This repository is the Gallery’s maintenance source. The academic website keeps a commit-pinned, hash-checked copy at `/gallery/`; upstream changes require separate review and deployment.

```sh
python scripts/sync_website.py plan --website ../chutj.github.io --ref <commit>
python scripts/sync_website.py apply --website ../chutj.github.io --ref <commit>
```

Only committed versions can be synchronized. Private FIG imports, PDFs and review evidence stay outside this repository. See the [maintainer workflow](docs/maintainers.zh-CN.md).

## Licensing

Project code and documentation use the **MIT License**. Research figures and other third-party material are excluded and retain their individual licenses, attribution and modification notices. PaperMod has its own license.

See [LICENSE](LICENSE), [LICENSES.md](LICENSES.md) and each figure’s details. Rights questions: [chutj@foxmail.com](mailto:chutj@foxmail.com).
