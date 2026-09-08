# 3C-SiC：Unified BEC 与 Gamma 声子

两原子原胞，PBE、SG15 ONCV 赝势、7-au DZP 轨道，100 Ry，
Gamma 中心的 13x13x13 网格，SCF 阈值 1e-8。

按照[计算软件配置教程](../../../docs/cli_reference.zh-CN.md#计算软件路径配置)设置 ABACUS 与
PYATB 后，先复制一份干净输入作为工作目录：

```bash
cp -r run work
cd work
```

首先计算 BEC 与 Gamma 点力常数：

```bash
zstar bec pre --stru STRU
zstar bec run --dry-run
zstar bec run
zstar bec stat
zstar bec post
```

然后以完成的响应计算为数据源生成 IR 与 Raman 谱：

```bash
zstar spectra pre --root spectra --response .
zstar spectra run --root spectra
zstar spectra stat --root spectra
zstar spectra post --root spectra
```

`bec post` 输出 BEC、`BORN`、力常数和 Gamma 点模式。IR 使用模式频率与
BEC；`spectra run` 计算 Raman 额外需要的 PYATB 介电响应。`run/` 保留输入、
赝势和轨道，`results/` 保存已有结果，新计算全部位于 `work/`。保留谱学结果
位于 `results/spectra/`，同时提供数据表及 PNG、PDF、SVG 格式的谱图。

熟悉各阶段后，可在案例目录执行 `bash run.sh --with-spectra` 完成同一套断点
续算流程；添加 `--dry-run` 可以只预览而不启动求解器。
Unified 自动选取两个位移，对照的 Cartesian 中心差分需要十二个位移；
两者均另算 `0.no-move`。从仓库根目录执行
`python examples/Benchmarks/run_control.py SiC` 可运行对照组。

此处核验原始与投影后的 BEC、Gamma Hessian、光学模式及静态声子介电响应，
是同设置下的数值一致性验证，不代表与实验的误差。
完整机时、计数及离线验证方法见[效率基准教程](../../Benchmarks/README.zh-CN.md)。

Unified 结果中 Si/C 的对角 BEC 分别为符号相反的 2.70094 e，三个同时具有
IR 与 Raman 活性的光学模式简并于 772.645 cm^-1。
