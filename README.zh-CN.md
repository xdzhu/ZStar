<p align="center">
  <img src="docs/logo.png" alt="ZStar 标志" width="160">
</p>

<h1 align="center">ZStar</h1>

<p align="center">
  面向极化、Born 有效电荷、介电与压电响应以及红外与拉曼谱的统一工具包。
</p>

<p align="center">
  <a href="https://pypi.org/project/zstar/"><img alt="PyPI" src="https://img.shields.io/pypi/v/zstar"></a>
  <a href="https://pypi.org/project/zstar/"><img alt="Python" src="https://img.shields.io/pypi/pyversions/zstar"></a>
  <a href="LICENSE"><img alt="许可证" src="https://img.shields.io/badge/license-GPL--3.0-green"></a>
</p>

<p align="center">
  <a href="README.md">English</a> | 简体中文 |
  <a href="docs/user_guide.zh-CN.md">完整手册</a> |
  <a href="docs/README.zh-CN.pdf">PDF</a>
</p>

## 快速上手

双原子 **3C-SiC** 案例从同一套对称性适配计算中得到 BEC 和 Gamma 点声子，
随后生成 IR 与 Raman 谱。案例已附 ABACUS 输入、SG15 赝势、DZP 轨道及参考结果。

### 1. 安装

不需要案例时，直接执行 `pip install zstar`。如需复现 SiC：

```bash
git clone https://github.com/xdzhu/ZStar.git
cd ZStar
pip install .
```

要求 Python 3.9 或更高版本；核心对称性处理使用 spglib，不强制依赖 pymatgen。
案例放在 GitHub，不包含在 PyPI wheel 中。

### 2. 配置计算软件

另行安装 [ABACUS](https://github.com/deepmodeling/abacus-develop)
（推荐 [LTSv3.10.0](https://github.com/deepmodeling/abacus-develop/releases/tag/LTSv3.10.0)）
和 [PYATB](https://github.com/pyatb/pyatb)；Phonopy 会随 ZStar 安装。
按照[配置教程](docs/cli_reference.zh-CN.md#计算软件路径配置)设置可执行文件路径与 MPI/OMP，然后检查：

```bash
zstar config check
```

确认 ABACUS 和 PYATB 均显示为 `available` 后再继续。

### 3. 计算 BEC 与 Gamma 点声子

建立工作副本，不改动案例输入和已有结果：

```bash
cd examples/3D_Bulk/SiC
cp -r run work
cd work

zstar bec pre --stru STRU
zstar bec run --dry-run
zstar bec run
zstar bec stat
zstar bec post
```

`pre` 准备参考态及对称性适配位移；`run` 检查参考结构的带隙并执行计算；
`post` 同时重建 BEC 和 Gamma 点力常数。结果包括 `BEC.dat`、`BORN`、
`FORCE_CONSTANTS` 和 `qpoints.yaml`。Si/C 的对角 BEC 约为符号相反的
**2.70 e**，三重简并光学模式约为 **773 cm^-1**。再次执行会续算未完成阶段。

### 4. 生成 IR 与 Raman 谱

```bash
zstar spectra pre --root spectra --response .
zstar spectra run --root spectra
zstar spectra stat --root spectra
zstar spectra post --root spectra
```

IR 复用已完成的 BEC 和声子数据；Raman 在 Unified 路线中复用电子矩阵，
补充 PYATB 介电响应，不增加 SCF。谱图和数据分别写入 `spectra/ir/`、`spectra/raman/`。
无需运行 DFT 也可直接查看[已有 SiC 谱学结果](examples/3D_Bulk/SiC/results/spectra)。
命令预览、进度检查及可选的 `run.sh` 用法见[案例教程](examples/3D_Bulk/SiC/README.zh-CN.md)。

## Unified 响应计算框架

ABACUS + PYATB 核心路线采用 Phonopy 对称性适配位移，从同一套极化与力
计算中同时重建 BEC/APT 和区中心力常数，复用电子矩阵得到非共振 Raman 导数。

![ZStar Unified 工作流](docs/paper_figures/unified_workflow.png)

流程从 `0.no-move` 开始，检查带隙并复用收敛电荷密度的副本，支持串行续算。
重建采用真实位移和对称性，保留原始/求和规则修正后的张量及残差诊断。

| 功能 | 主要结果 |
| --- | --- |
| 极化与 BEC/APT | 分支匹配后的极化、全张量、`BORN` 与响应记录 |
| Gamma 点声子 | 力常数、模式频率、本征矢与不可约表示 |
| IR 与 Raman | 模式电荷、振子强度、Raman 张量、偏振/展宽光谱 |
| 介电响应 | 电子、声子、静态及频率相关响应 |
| 超胞声子 | 高对称路径声子能带、DOS、bulk NAC 与 LO-TO 劈裂 |
| 压电响应 | VASP 原生电子/离子/总压电 `e`，弹性响应及推导的 `d` |
| 极化相关静电势分析 | 平面分布、线剖面、真空势差与镜面非对称度 |

详见 [Unified BEC/声子](docs/research/shared_response/USAGE.zh-CN.md)、
[Unified 谱学](docs/unified_spectroscopy.zh-CN.md)与[数值验证](docs/validation.zh-CN.md)。

## 不同维度体系

周期方向采用 Berry 相位极化及 phase-wrapped 分支匹配；非周期方向采用
包含离子和电子贡献的实空间偶极。孤立分子的偶极响应由原子极化张量（APT）描述。

| `--dim` | 体系 | 响应处理与案例 |
| --- | --- | --- |
| `3` | 三维晶体 | Berry 相位极化；立方 BaTiO3、四方 HfO2、SiC |
| `2` | 二维片层 | 面内 Berry 相位、面外 cube 偶极；hBN、MoS2、alpha-In2Se3 |
| `1` | 一维链/管 | 轴向 Berry 相位、横向 cube 偶极；BN(9,0)、Sb2S3 |
| `0` | 分子 | 偶极导数与 APT；H2O、CH4 |

二维材料使用 `zstar bec pre --stru STRU --dim 2`，后续阶段保留该设置。
混合路线要求片层法向或一维周期轴与笛卡尔 `z` 对齐，并检查真空尺寸收敛性。

周期晶体的 BEC 采用极化指标在前的张量约定：

$$
Z^*_{\kappa,\alpha\beta}=\frac{\Omega}{e}\frac{\partial P_\alpha}{\partial u_{\kappa\beta}}.
$$

低维介电响应采用分子、线或片层极化率，而非依赖真空的 bulk 介电常数。
厚度转换及面外电场边界条件见[响应定义与单位](docs/response_conventions.md)。

## 代表性 BEC 与 APT 结果

案例库保留下列代表值对应的完整张量、计算设置及来源记录：

| 体系 | 泛函 | 代表性结果，单位 `e` |
| --- | --- | --- |
| [立方 BaTiO3](examples/3D_Bulk/cubic_BaTiO3) | PBEsol | `Z*(Ti) = 7.440`；`Z*(Ba) = 2.734` |
| [四方 HfO2](examples/3D_Bulk/t_HfO2) | PBEsol | `Z*(Hf,xx) = 5.394`；`Z*(Hf,zz) = 4.828` |
| [单层 hBN](examples/2D_Slab/hBN_unified) | PBE | `Z*(B,parallel) = 2.702`；`Z*(B,z) = 0.343` |
| [alpha-In2Se3](examples/2D_Slab/alpha_In2Se3_PBE) | PBE | `Z*(In(2),parallel) = 4.016`；`Z*(In(2),zz) = 0.278` |
| [BN(9,0)](examples/1D_Nanowire/BN_9_0) | PBE | `(Zrr,Ztt,Zzz)_B = (0.397,1.256,2.745)` |
| [H2O](examples/0D_Molecules/H2O_unified) | PBE | `q_GAPT(O) = -0.481`；`q_GAPT(H) = +0.240` |
| [CH4](examples/0D_Molecules/CH4_unified) | PBE | `q_GAPT(C) = -0.021`；`q_GAPT(H) = +0.005` |

以上为 ABACUS + PYATB 结果；分子 `q_GAPT = Tr(APT)/3` 不是周期晶体 BEC。
H2O/CH4 另附 HSE cube 偶极 APT 摘要，见[分子教程](docs/molecular_spectroscopy.zh-CN.md)。

## IR、Raman 与介电响应

![体材料、二维片层、一维纳米线与分子的 IR 和 Raman 谱](docs/paper_figures/spectroscopy_across_dimensions.png)

四行展示四方 HfO2（PBEsol）、MoS2（PBE-D3(BJ)）、Sb2S3 和 CH4。
[谱学案例](examples/IR_Raman_Spectra)保留模式归属与参考数据，包括 Sb2S3
公开计算数据集参考及实际存在的 Raman 强度差异。

从快速上手已完成的 BEC/Gamma 结果继续计算静态及频率相关介电响应：

```bash
zstar dielectric static --qpoints qpoints.yaml --born BEC.dat --dielectric BORN --dim 3
zstar dielectric freq --qpoints qpoints.yaml --born BEC.dat --dielectric BORN --dim 3
```

![Bulk 与二维材料介电响应案例](docs/paper_figures/dielectric_response_examples.png)

HfO2 展示电子加声子响应，MoS2 展示声子片层极化率。程序输出静态张量、
实部/虚部数据及 PNG/PDF/SVG 图片；阻尼、截断、归一化与光学常数见
[介电教程](docs/dielectric_response.zh-CN.md)。

有限波矢声子能带/DOS 需要**独立超胞计算**，不只需要 Gamma 力常数。
[声子教程](docs/phonon_spectrum.zh-CN.md)涵盖自动扩胞、自备 CPU/GPU `INPUT`、
路径和 bulk NAC；有相容 `BORN` 时给出不含/包含 NAC 及 LO-TO 劈裂叠加图。
bulk NAC 不用于片层或一维体系。

## 计算器后端与压电响应

其他后端使用各自求解器，不一定采用 Unified 有限位移路线。
需要可选 VASP 读取器时，安装 `zstar[vasp]`。

| 计算器 | 支持的路线 | 教程 |
| --- | --- | --- |
| ABACUS + PYATB | Unified BEC/APT、Gamma 声子、IR/Raman、介电响应 | [统一流程](docs/research/shared_response/USAGE.zh-CN.md) |
| VASP | 原生 bulk BEC/介电/声子、IR、压电/弹性张量，模式位移 Raman | [原生响应](docs/vasp_native_response.zh-CN.md) |
| CP2K | 偶极 BEC/APT 及原生谱学路线 | [BEC](docs/cp2k_bec.zh-CN.md)、[谱学](docs/calculator_spectroscopy.zh-CN.md) |
| Quantum ESPRESSO | 原生 DFPT BEC、介电与 IR 收集 | [后端教程](docs/calculator_independent_backends.zh-CN.md) |

例如，从已准备的 VASP 输入获取含离子弛豫的压电 `e`：

```bash
zstar bec pre --calculator vasp --input-dir input --root piezo --piezo
zstar bec run --root piezo
zstar bec post --root piezo
```

VASP 的 LDA/GGA 路线采用原生 DFPT/离子响应；`--elastic` 还获取弹性矩阵及 `d`。
[SiC](examples/VASP_Native_Response/3C_SiC)和[AlN](examples/VASP_Native_Response/AlN)
保留验证结果。Raman 仍需模式位移计算；用户自行提供获许可的 `POTCAR`。
泛函及低维适用边界见教程。

## 自有结构与集群作业

在工作目录准备 ABACUS 输入及资源；若赝势、轨道位于其他位置，生成时指定目录：

```bash
zstar bec pre --stru STRU --pp /path/to/PSEUDO --orb /path/to/ORBITAL
zstar bec job --system slurm
```

匹配不唯一时会报出解决指引，不修改原始 `STRU`。可执行文件与 MPI/OMP
在 `zstar config` 中设置；队列、资源、module 及环境命令放入 header：
**Specified**（`--header`）>
**Current**（`./header.sh`）> **Global**（`~/.zstar/header.sh`），不合并。
都没有时，生成的任务脚本提供可编辑模板。

`job` 仅生成脚本：检查、提交、等待完成后再 `post`。支持 shell、Slurm 与 Torque/PBS。
[header 教程](docs/job_headers.zh-CN.md)与[CLI 参考](docs/cli_reference.zh-CN.md)
说明资源及全局 PP/ORB 设置。新 PYATB 使用静态直算，旧版使用紧凑光学网格，
见[兼容说明](docs/user_guide.zh-CN.md#pyatb-新旧版本兼容)。

## 实测计算效率

同设置 Separate/Unified 基准中，BEC/APT 加 Gamma 声子最高加速 **3.98 倍**，
IR/Raman 最高加速 **8.35 倍**。成对柱标出归一化成本、求解器 CPU 核时和加速比。

![Separate 与 Unified 工作流实测成本](docs/paper_figures/unified_efficiency_benchmarks.png)

[基准归档](examples/Benchmarks/README.zh-CN.md)保留任务数、统计边界及数据；
加速比取决于体系与设置。

## 极化相关静电势分析

`zstar pot` 对 MoS2、alpha-In2Se3 及 SnS/SnSe/SnTe 静电势 cube 绘制平面图、
线剖面，并分析真空势差与单周期镜面非对称度。

![极性片层及面内静电势案例](docs/paper_figures/potential_examples_2d.png)

alpha-In2Se3 的真空势差约 **1.221 eV**，MoS2 则近乎对称；见
[静电势教程](docs/potential_examples.zh-CN.md)和[可运行案例](examples/Electrostatic_Potential)。

## agent skill

安装随软件提供的 `$run-zstar-workflows`，然后新建智能体会话：

```bash
zstar skill install
```

示例请求：“使用 $run-zstar-workflows，将自带 SiC 输入复制到新工作目录，
检查计算软件配置，逐步完成 BEC、Gamma 点声子及 IR/Raman 计算，报告张量、
频率和输出路径。”

尚未安装 ZStar 时，[从零开始的提示词](docs/user_guide.zh-CN.md#5-让智能体运行同一案例)
明确指定源码、Python 环境、skill 与工作目录；升级及预检查见
[skill 教程](docs/agent_skill.zh-CN.md)。

## 文档与命令总览

[完整中文手册](docs/user_guide.zh-CN.md)（[PDF](docs/README.zh-CN.pdf)）|
[Full English manual](docs/user_guide.md)（[PDF](docs/README.en.pdf)）|
[按任务查找文档](docs/README.zh-CN.md) | [案例库](examples/README.zh-CN.md)

案例分别提供干净输入 `run/`、已有结果 `results/` 和可续算的 `run.sh`。
建议先理解上面的逐步操作，再用一键脚本。

| 命令族 | 功能 |
| --- | --- |
| `zstar bec pre/job/run/stat/post` | 极化、BEC/APT、Unified Gamma 结果或原生后端响应 |
| `zstar phonon pre/job/run/stat/post/irrep/spectrum` | 超胞力、模式、活性分类、声子能带及 DOS |
| `zstar spectra pre/job/run/stat/post` | IR 与 Raman 准备、执行、收集及绘图 |
| `zstar dielectric static/freq/optics` | 静态/频率响应及光学常数 |
| `zstar config init/show/set/check` / `zstar backend list` | 配置与计算软件可用性 |
| `zstar response` / `zstar density` | 响应交换与密度导出适配 |
| `zstar stru convert/wyckoff` | 结构转换与 Wyckoff 分析 |
| `zstar data db/qnep` | 可追溯 BEC 数据库及 qNEP 导出 |
| `zstar skill install/path/preflight` / `zstar pot` | agent skill 与静电势分析 |

[CLI 参考](docs/cli_reference.zh-CN.md)列出全部子命令及别名；详细设置与物理约定见长版教程。

## 引用与许可证

使用时请引用 ZStar 及实际调用的电子结构和晶格动力学软件，见
[CITATION.cff](CITATION.cff)。软件采用 [GPL-3.0](LICENSE) 许可证。
Copyright (c) Xudong Zhu.
