# 维护与发布

## 三处职责

- FIG：维护原始图片、论文 PDF 与原始 Markdown；Website 和本项目只读使用。
- Website 本地 `.gallery-local/`：增量导入、PDF 关联、英文草稿、私有证据、待批准批次。
- `sci-figure-gallery`：公共代码与已明确批准的数据维护源；网站通过固定版本同步接入。

网站地址始终为 `https://chutj.github.io/gallery/`。独立仓库 CI 只验证，不部署第二个网站。Home、GEE Access 和 FIG 私人资料不在本仓库。

## 修改界面或公开说明

1. 在本仓库修改 Gallery 代码，测试并审核 PR。
2. Commit / Push 本仓库，确认其 CI 通过。
3. 执行同步计划与应用，使用明确的提交：

```powershell
python scripts/sync_website.py plan --website ../chutj.github.io --ref <commit>
python scripts/sync_website.py apply --website ../chutj.github.io --ref <commit>
```

4. 在 Website 检查受管理文件和 `gallery-component.lock.json`，运行干净生产构建，再 Commit / Push 网站。

同步默认不 Commit、不 Push、不删除文件。它只写组件清单和公开媒体清单指定的文件，并保留替换前备份。若网站受管理文件被手工修改，校验会停止，避免覆盖已有工作。不要同时在两个仓库手工维护同一份 Gallery 代码。

新仓库提交不自动触发线上更新。网站构建不下载最新 main，也不读取本地绝对路径；固定版本和内容哈希都可由干净检出校验。

## 新增论文和图片

继续在 Website 运行现有 Prepare Update：导入 FIG、定位 PDF 图注、整理英文信息和许可证据。原始资料保持只读。收到明确人工批准后，使用现有私有审批文件生成公共发布包：

```powershell
python scripts/prepare_approved_release.py --website ../chutj.github.io --approval .gallery-local/updates/<batch>/approval.json --output ../chutj.github.io/.gallery-local/release-bundles/<batch>
python scripts/sync_website.py capture-public --bundle ../chutj.github.io/.gallery-local/release-bundles/<batch> --reviewed
```

桥接脚本复用所有者本地 `gallery_workflow.py` 的明确 ID、图片版本、元数据、PDF证据和审批校验，不猜测许可，也不批准新图。公开构建和普通贡献者不需要这一私人适配器。

`private-bindings.json` 保留在 Website 忽略目录中，不能上传或手工复制进本仓库。capture-public 只读取三个公开 JSON 和经白名单校验的媒体，不复制证据、PDF或其他文件。

审核本仓库新增的公开文件，测试，Commit / Push 并确认 CI。随后固定此提交同步网站，并应用相同发布包的私人证据绑定：

```powershell
python scripts/sync_website.py apply --website ../chutj.github.io --ref <commit> --release-bundle ../chutj.github.io/.gallery-local/release-bundles/<batch>
```

最后在 Website 做生产构建和 Git 提交审查，确认后部署。新的双仓库顺序取代直接执行旧单仓库 `publish --execute`；直接修改网站的托管 JSON 会被版本锁拦截。日常仍可以告诉 Codex：“检查 FIG 新增内容，准备本次 Figure Gallery 更新。”批准发布时需要完成上述两仓库顺序。

## 安全与失败处理

- 代码 MIT 不覆盖科研图片；逐图许可、版本、第三方材料和实际用途继续审核。
- 同一篇论文的新图不会继承旧图审批。
- 删除或撤回媒体需要单独审查；同步不会自动删除旧文件。
- 失败时先查看命令的 STOP 原因、Git 状态以及 Website `.gallery-local/component-sync/` 的备份，不 force push，不自动回滚覆盖。
- CODEOWNERS 用于指定代码审阅人；是否强制审阅取决于 GitHub 分支规则，不能把文件本身当成已启用分支保护。
