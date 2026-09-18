<p align="center">
  <img src="docs/logo.png" alt="ZStar 标志" width="128">
</p>

<h1 align="center">ZStar</h1>

<p align="center">
  面向极化、Born 有效电荷、介电与压电响应以及红外与拉曼谱的统一工具包。
</p>

<p align="center">
  <a href="https://pypi.org/project/zstar/"><img alt="PyPI" src="https://img.shields.io/pypi/v/zstar"></a>
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
zstar bec run
zstar bec post
```

结果包括 `BEC.dat`、`BORN`、`FORCE_CONSTANTS` 和 `qpoints.yaml`。
Si/C 的对角 BEC 约为符号相反的 **2.70 e**，三重简并光学模式约为 **773 cm^-1**。
使用 `zstar bec stat` 查看进度；重复执行会跳过已完成阶段。

### 4. 生成 IR 与 Raman 谱

```bash
zstar spectra pre --root spectra --response .
zstar spectra run --root spectra
zstar spectra post --root spectra
```

谱图和数据分别写入 `spectra/ir/`、`spectra/raman/`。
无需运行 DFT 也可直接查看[已有 SiC 谱学结果](examples/3D_Bulk/SiC/results/spectra)。
命令预览、进度检查及可选的 `run.sh` 用法见[案例教程](examples/3D_Bulk/SiC/README.zh-CN.md)。

## agent skill

执行 `zstar skill install`，新建智能体会话并调用 `$run-zstar-workflows`。
[示例提示词](docs/user_guide.zh-CN.md#5-让智能体运行同一案例)说明如何让智能体从零安装
ZStar 和 skill、配置计算软件并复现 SiC。

## 案例与文档

![体材料、二维片层、一维纳米线与分子的 IR 和 Raman 谱](docs/paper_figures/spectroscopy_across_dimensions.png)

- [完整手册](docs/user_guide.zh-CN.md)（[PDF](docs/README.zh-CN.pdf)）：详细工作流、BEC/APT 结果、效率基准及验证图。
- [文档索引](docs/README.zh-CN.md)：配置、维度约定、作业系统及各项功能教程。
- [案例库](examples/README.zh-CN.md)：bulk、slab、wire 与分子案例，均提供 `run/`、`results/` 和 `run.sh`。
- [VASP 原生响应](docs/vasp_native_response.zh-CN.md)：bulk BEC、介电、声子、压电及弹性工作流；[其他计算器](docs/calculator_independent_backends.zh-CN.md)。

## 引用与许可证

使用时请引用 ZStar 及实际调用的计算软件，见 [CITATION.cff](CITATION.cff)。
软件采用 [GPL-3.0](LICENSE) 许可证。
