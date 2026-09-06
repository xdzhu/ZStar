# Unified IR 与 Raman 工作流

[English](unified_spectroscopy.md)

本教程对应当前源码快照。在仓库中执行 `python -m pip install -e .` 安装；
旧的公开安装包可能尚不包含本次 Unified 谱学升级。

![统一响应工作流](paper_figures/unified_workflow.png)

ABACUS + PYATB 路线使用同一套对称性约化位移，同时获得 BEC/APT、Gamma 点
力常数、IR，以及静态非共振 Placzek Raman。Raman 仍然需要电子介电响应的导数，
并非仅凭 BEC 就能得到。保留各位移的 Hamiltonian、overlap 和 position 矩阵后，
这些响应可以由 PYATB 后处理得到，不新增 SCF；额外 PYATB 机时计入效率统计。
PYATB 位于另一 Python 环境时，使用其解释器执行当前 ZStar 安装中的精度适配器，
避免误加载那个环境里的旧 ZStar。启动命令应直接指向 PYATB 可执行文件，
不要使用无法解析的复杂 shell 管道。

## 运行

在含 ZStar、Phonopy、PYATB 的环境中，用 `zstar config` 设置 ABACUS 启动命令。
输入应是已优化、保持绝缘、参数已收敛的结构。一维周期方向为 z，二维法向为 z。
即使实际只采样 Gamma 点，PYATB 矩阵导出仍要求 `gamma_only=0`，准备阶段会
在生成的输入中自动设置，原始 INPUT 不变。谱图文件导出不依赖 GUI 或 Tcl/Tk。

```bash
zstar bec pre --stru STRU --input INPUT --dim 3
zstar spectra pre
zstar spectra run
zstar spectra post
```

二维、一维、分子分别在 BEC 准备时指定 `--dim 2`、`1`、`0`。谱学自动继承维度和
结构，在独立的 `spectra/` 中工作。`run` 补齐尚未完成的基准态及位移计算，包含
基准态 band gap 检查，然后计算额外的静态介电响应；`post` 在需要时收集 BEC 和声子。

复用已经完成的计算：

```bash
zstar spectra pre --response /path/to/completed/bec
zstar spectra run
zstar spectra stat
zstar spectra post --temperature 300 --laser 532 --broadening 8
```

温度单位 K，激光波长单位 nm，Lorentzian 展宽参数单位 cm^-1；`--points` 设置谱线网格。
准备时用 `--kind ir` 可跳过 Raman 所需的介电导数步骤。矩阵丢失时会明确报错，
不能仅从 BEC 表恢复这些电子响应。

## 作业与续算

```bash
zstar spectra job --system slurm
```

沿用 [Specified / Current / Global header](job_headers.zh-CN.md) 与可执行文件配置。
提交前检查 `spectra/run_zstar_spectra.slurm`。`stat` 逐项列出源 SCF、极化和 Raman
静态响应是否完成；再次运行会校验并跳过已完成阶段。每个静态阶段保存请求、完成或
失败记录，用哈希检测输入或结果变化。工作锁阻止同一目录并发写入；确认进程结束后
才可删除遗留锁。

矩阵与结构资源采用私有复制，不用软链接，也不覆盖源 BEC 输入、矩阵或 cube。
新版 PYATB 使用直接静态截距；旧版从最小光学窗口提取零频响应。精度适配器保留
原始舍入文件及高精度张量，不修改数值内核。

## 结果与约定

- `ir/`：频率、振子强度、谱线数据和图像。
- `raman/`：模式张量、Placzek 活性、谱线及原子介电导数。
- `response.json`：可交换的响应数据、单位与来源。
- `spectra_result.json`：秩、拟合残差与刚体模式分类。
- `static/<stage>/`：额外的 PYATB 计算及完整性记录。

导数采用实际写出的结构差分向量，三阶张量的每个指标都按对称操作变换，再与质量
归一化本征矢收缩。三维、二维、一维、分子的系数依次为 1、Lz、A/(4 pi)、V/(4 pi)，
与[响应约定](response_conventions.md)一致；微扰时晶胞固定。分子 IR 从 APT 得到
偶极导数，不除以超胞体积。Raman 平移和规则残差保留报告，不暗中投影。
平移、转动模式由质量加权重叠识别；内部虚频和不明确的模式混合会阻止结果收集。

## 对照与案例

`zstar spectra pre --method mode --stru STRU --qpoints qpoints.yaml` 保留逐模式差分。
VASP、CP2K、QE 保持各自已支持的工作流，不会被自动替换成 ABACUS 算法。
这里不宣称实现共振 Raman 或完整声子能带。

四维案例位于 `examples/IR_Raman_Spectra/` 下的 `Bulk_HfO2`、`2D_MoS2`、
`Nanowire_Sb2S3`、`Molecule_CH4`。各自保留 `run/` 清洁输入及赝势轨道、`results/`
参考结果、`run.sh`。`bash run.sh --dry-run` 预览，`bash run.sh` 默认 Unified；
`bash run.sh --method mode --work mode_control` 执行独立模式对照。更换取样方法时使用
新工作目录，不在已有参考结果中继续计算。
