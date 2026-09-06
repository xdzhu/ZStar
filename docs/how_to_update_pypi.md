# ZStar 的 GitHub 与 PyPI 更新流程

本文档用于以后自行发布 ZStar。先设置仓库根目录：

```powershell
$RepoRoot = "C:\path\to\zstar"
Set-Location $RepoRoot
```

## 基本约定

- `examples/` 是 GitHub 上公开的案例库；wheel 和 PyPI 源码包均不包含它。
  完整审稿交付包另附案例，并区分 DFT 重跑、离线重建和需用户提供 cube 的分析。
- `dist/`、`build/` 和 `*.egg-info/` 是本地构建产物，不提交 GitHub。
- 调度脚本由 ZStar CLI 按系统自动生成；仓库不再维护站点专用的旧作业模板。
- 开发和测试使用 `zstar-test` 环境。
- 构建和上传可以使用安装了 `build` 与 `twine` 的独立发布环境。
- PyPI 已发布的文件不可覆盖。

## 什么时候需要修改版本号

仅向 GitHub 提交代码或文档时，不必修改版本号。

只要希望 PyPI 页面或安装包发生变化，即使只修改 README/项目描述，也必须发布一个新版本。PyPI 不允许用同一版本号重新上传 wheel 或源码包。

建议遵循：

- 修复错误或只改文档：补丁版本，例如 `0.1.0 -> 0.1.1`。
- 增加向后兼容的新功能：次版本，例如 `0.1.0 -> 0.2.0`。
- 引入不兼容接口：主版本。

版本号需要同时修改：

- `pyproject.toml` 中的 `project.version`
- `zstar/__init__.py` 中的 `__version__`
- `CITATION.cff` 中的版本与日期
- `CHANGELOG.md` 中的发布记录

还应同步当前 README、教程和稿件中的安装版本、GitHub 标签与图片 URL。
历史验证报告、原始计算的版本号及哈希保留，不做全局替换。

## 1. 检查工作区

```powershell
conda activate zstar-test
Set-Location $RepoRoot

git status --short
git diff --check
```

确认没有误加入：

- `dist/`
- `build/`
- 临时输出和账号凭据

## 2. 运行本地测试

```powershell
python -m compileall -q zstar tests
python -m pytest tests -q
python -m zstar --version
python -m zstar --help
python -m zstar spectra run --help
python -m zstar skill path
python -m zstar skill preflight --root . --lane bec --dim bulk
```

需要外部程序的例子应在仓库的 `examples/` 中验证。至少确认：

- `zstar bec post` 能处理已有极化结果。
- 默认绝缘性门控只对 `0.no-move` 执行一次普通 `--band`。
- `zstar bec stat` 能识别完成、失败和恢复状态。
- 新旧 PYATB 环境都能读取电子介电张量。

### 独立安装验收

从最终 wheel 安装到新建环境，不使用 `--system-site-packages` 或 editable 安装。
在仓库外运行 `tools/release_acceptance.py smoke`，然后用同一解释器运行
`tools/release_acceptance.py tests --repo 仓库路径 --output 验收输出目录`。
脚本先加载已安装的 ZStar，再开放测试辅助工具目录，并记录所有 ZStar 模块路径。
Linux 上运行 `tools/release_example_audit.py --repo 仓库路径 --output dry-runs.json`，
逐例检查 `bash run.sh --dry-run`。再运行四个 Unified 谱学案例的 `--post-only`，
以及一个短案例的实际计算和重复执行，确认续算不会重新运行已完成的求解器阶段。

分别记录所用 Phonopy 版本、测试命令及数量；不要把不同范围的历史测试总数混用。

Windows 上必须额外核对 Git 索引的实际大小写，而不能只检查文件是否存在：
`python -m pytest tests/test_examples_layout.py -q` 包含这项检查。
0.3.0 曾因索引中的 `3d_bulk` 与清单中的 `3D_Bulk` 不一致而在 Linux 失败，
0.3.1 已修复。Windows dry-run 应明确选择 Git Bash，例如给
`tools/release_example_audit.py` 添加 `--shell "C:/Program Files/Git/bin/bash.exe"`，
并将已安装 ZStar 的环境加入 PATH，避免误调用看不到 Windows 环境的 WSL Bash。

先等待 main 分支的 Linux CI 和独立安装检查通过，再创建版本标签；标签触发
Release 构建和自动更新说明。确认 Release 构建成功后再上传 PyPI。
main 上仅修改手册时会自动构建可下载的 Actions 产物，不会覆盖旧版本发布文件。

## 3. 更新中英文 README 与 PDF

编辑：

- `README.md`
- `README.zh-CN.md`
- `README_PYPI.md`

重新渲染：

```powershell
node docs\render_readme_pdfs.mjs
```

输出：

- `docs/README.en.pdf`
- `docs/README.zh-CN.pdf`

应把 PDF 转成图片进行目视检查，确认没有截断、重叠、乱码或过宽表格：

```powershell
pdftoppm -png -r 120 docs\README.en.pdf tmp\pdfs\README-en
pdftoppm -png -r 120 docs\README.zh-CN.pdf tmp\pdfs\README-zh
```

## 4. 检查 PyPI 描述

由于仓库可能是私有的，`README_PYPI.md` 不应使用：

```html
<img src="docs/logo.png">
```

也不应使用私有仓库的 `raw.githubusercontent.com` 地址。PyPI 访问者没有仓库登录权限，图片会失效。

可选方案：

1. 不在 PyPI 描述中显示 logo，这是当前默认方案。
2. 将 logo 放在独立的公开仓库或长期稳定的公共 HTTPS 静态资源服务中。
3. 把该公开 URL 写入 `README_PYPI.md`。

PyPI 不会为安装包中的 `docs/logo.png` 提供可直接嵌入项目页面的稳定资源 URL。

## 5. 清理旧构建并打包

不要删除源码目录。只清理已确认位于项目根目录下的构建产物：

```powershell
Set-Location $RepoRoot
Remove-Item -Recurse -Force -LiteralPath .\dist -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force -LiteralPath .\build -ErrorAction SilentlyContinue
Get-ChildItem -Directory -Filter *.egg-info | Remove-Item -Recurse -Force

python -m build
```

`dist/` 中应出现：

```text
zstar-X.Y.Z-py3-none-any.whl
zstar-X.Y.Z.tar.gz
```

## 6. 检查发布包内容

```powershell
python -m twine check dist\*
python -m zipfile -l dist\zstar-X.Y.Z-py3-none-any.whl
```

确认：

- 包中有 `zstar/` 模块和必要文档。
- 包中有 `zstar/agent_skills/run-zstar-workflows/`，且不含
  `__pycache__` 或 `*.pyc`。
- 包中没有 `examples/`、`dist/`、远端计算输出或凭据。
- `README_PYPI.md` 渲染检查通过。

建议创建临时环境做安装测试：

```powershell
python -m venv tmp\release-smoke
tmp\release-smoke\Scripts\python -m pip install --upgrade pip
tmp\release-smoke\Scripts\python -m pip install dist\zstar-X.Y.Z-py3-none-any.whl
tmp\release-smoke\Scripts\zstar --version
tmp\release-smoke\Scripts\zstar --help
tmp\release-smoke\Scripts\zstar skill install --dest tmp\release-smoke-skill
$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME '.codex' }
python (Join-Path $codexHome 'skills\.system\skill-creator\scripts\quick_validate.py') tmp\release-smoke-skill\run-zstar-workflows
```

## 7. 提交并推送 GitHub

只暂存本次需要的文件：

```powershell
git add README.md README.zh-CN.md README_PYPI.md CHANGELOG.md pyproject.toml
git add zstar tests docs README*.md MANIFEST.in
git status --short
git diff --cached --check
```

提交并推送：

```powershell
git commit -m "Release ZStar X.Y.Z"
git push origin main
```

`examples/` 是公开案例内容，应在提交前检查其 manifest、输入路径和参考结果；
`dist/` 仍不提交。

## 8. 上传 PyPI

推荐使用 PyPI API token，不要把 token 写入仓库。

可先测试：

```powershell
python -m twine upload --repository testpypi dist\*
```

正式上传：

```powershell
python -m twine upload dist\*
```

用户名使用：

```text
__token__
```

密码使用 PyPI 生成的 token。

## 9. 发布后验证

等待 PyPI 页面刷新后：

```powershell
python -m venv tmp\pypi-smoke
tmp\pypi-smoke\Scripts\python -m pip install --upgrade pip
tmp\pypi-smoke\Scripts\python -m pip install --no-cache-dir zstar==X.Y.Z
tmp\pypi-smoke\Scripts\zstar --version
tmp\pypi-smoke\Scripts\zstar --help
```

同时检查：

- PyPI 项目描述中的表格、代码块和链接。
- GitHub 中英 README 与 logo。
- GitHub PDF 链接。
- 仓库提交中包含整理后的 `examples/`，但不包含 `dist/`、scratch 输出或凭据。

## 常见问题

发布候选版可使用 `tools/release_acceptance.py` 在独立环境中检查 wheel。
完整研究辅助脚本测试额外需要 `tools/requirements-research-tests.txt`，使用
`tests --include-tools`；这不增加普通用户安装 ZStar 的依赖。

### PyPI 提示文件已经存在

同一版本号不能重复上传。提高版本号、重新构建并再次上传。

### GitHub 能显示 logo，但 PyPI 不能

相对路径图片只对仓库页面有效。私有 GitHub 原始文件对未登录的 PyPI 访问者不可见，应使用公开 HTTPS URL 或不显示 logo。

### 只改 README，是否需要更新软件版本

只推送 GitHub：不需要。

要让 PyPI 页面同步新的 README：需要，因为必须上传一个新的、版本号不同的发布包。
