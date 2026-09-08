# ZStar 可复现实例库

这里是 ZStar 公开发布的精简案例库。每个案例保留可运行的输入、赝势与
轨道、来源说明以及紧凑的参考结果；完整的 ABACUS、PYATB、CP2K 或 VASP
scratch 目录不放入仓库。

## 目录结构

| 目录 | 范围 | 案例 |
|---|---|---|
| `3D_Bulk/` | 体材料 BEC 与介电响应 | 四方及立方 BaTiO3、HfO2、3C-SiC |
| `2D_Slab/` | 薄层及与真空无关的面响应 | MoS2、hBN、alpha-In2Se3 |
| `1D_Nanowire/` | 周期性一维响应 | BN(9,0)、Sb2S3；早期 GaAs 示例 |
| `0D_Molecules/` | 分子 APT、IR 与 Raman | H2O、CH4、CO2 |
| `backend_examples/` | 计算器后端验证 | CP2K BEC/IR/Raman、ABACUS/VASP 的 SiC 与 HfO2 基准 |
| `IR_Raman_Spectra/` | 一键 IR 与 Raman 工作流 | HfO2、MoS2、Sb2S3、CH4、BN 管；早期 GaAs 示例 |
| `Electrostatic_Potential/` | 基于 cube 的静电势分析 | MoS2、alpha-In2Se3、GeS、SnS、SnSe、SnTe |

机器可读索引为 `manifest.json`；旧目录到新目录的映射见 `path_migration.json`。
`Benchmarks/` 保留效率对照的统一索引，材料输入归入四个维度目录。原始结果
记录中的历史路径作为来源证据保留，不改写计算历史。
每个案例都包含干净的 `run/` 输入目录、
保存已有计算结果的 `results/` 目录、中英文 README，以及案例根目录的
`run.sh`。参考结果用于复现和接口检查，不能替代用户在新机器上的收敛性
测试。

## 复现层级

完整的目录不等于每个案例都包含上游 DFT 原始数据，运行前请先区分：

- **重新计算电子结构**：配置外部计算器后，用提供的输入和资源文件运行。
  VASP 的授权输入仍须由用户提供。
- **离线重建**：利用保留的响应观测或 cube 重新生成数值结果，不运行 DFT。
  四个 Unified 谱学案例均支持 `bash run.sh --post-only`，并核对输入哈希。
- **已有结果分析**：查看保留的表格和图片，或提供同类计算输出后重新处理。
  SnS、SnSe、SnTe 静电势案例使用 `bash run.sh --cube /path/to/ElecStaticPot.cube`。

MoS2、In2Se3、GeS 的静电势脚本同样需要已有 cube，不会自动启动上游 SCF。
`GeS_nonpolar` 提供独立脚本和压缩 cube。具体以各案例 README 为准。

## 快速开始

双原子 3C-SiC 是最短的完整 BEC 与谱学案例。配置 ABACUS 和 PYATB 后执行：

```bash
cd examples/3D_Bulk/SiC
bash run.sh --with-spectra --dry-run
bash run.sh --with-spectra
```

脚本会在案例旁边创建 `work/`，保留已有阶段，并支持中断后续算。
`work/` 保存 Unified BEC/Gamma 响应，`work/spectra/` 保存 IR/Raman 谱图。
输入与输出的具体说明见该案例 README。其他案例沿用相同的 `run/`、`results/`
和 `work/` 约定，并在各自 README 中说明维度相关差异。

## 可复现约定

- 请从案例工作目录执行命令，以保证相对路径能够找到赝势和轨道。
- 不要修改 `run/` 和 `results/`，新结果写入 `work/`。
- `dim=0/1/2/3` 分别表示分子、周期性纳米线、薄层和体材料。
- `dim=2` 的面内极化使用 Berry phase，面外极化使用电荷密度 cube 的
  实空间积分。
- `dim=1` 的横向偶极使用实空间积分，不应启用三维 bulk NAC 修正。
- 体材料介电常数和高 K 排序必须基于收敛且绝缘的状态；分子、纳米线和
  薄层结果应使用各自的本征维度归一化。

## 后端验证

`backend_examples/` 说明如何连接 CP2K 和 VASP。VASP 的授权文件（例如
`POTCAR`）不会被重新分发。更多说明见
`docs/calculator_independent_backends.md`、`docs/calculator_spectroscopy.md`、
`docs/spectroscopy_backend_benchmark.zh-CN.md`
以及各案例 README。

`Electrostatic_Potential/SnS`、`SnSe` 和 `SnTe` 是紧凑的后处理案例：保留已核验
的轮廓和图像，但原始 cube 与上游大型 SCF 输出不放入公开包。
