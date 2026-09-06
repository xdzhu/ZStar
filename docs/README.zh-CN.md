# ZStar 使用手册

[English](README.md) | [项目首页](../README.zh-CN.md) |
[中文 PDF](README.zh-CN.pdf) | [English PDF](README.en.pdf)

本手册对应已发布的 **ZStar 0.3.1**，安装命令为 `pip install zstar==0.3.1`。
默认路线需要另行安装 ABACUS 和 PYATB；安装 ZStar 的 Python 包不会安装这些求解器。

## 按任务查找

| 任务 | 教程 | 主要入口 |
| --- | --- | --- |
| 同一套计算得到 BEC/APT 与 Gamma 声子 | [Unified BEC 与声子](research/shared_response/USAGE.zh-CN.md) | `zstar bec pre/run/stat/post` |
| Unified 位移集合上的 IR 与 Raman | [Unified 谱学](unified_spectroscopy.zh-CN.md) | `zstar spectra pre/run/stat/post` |
| 静态及频率相关介电响应 | [介电响应](dielectric_response.zh-CN.md) | `zstar dielectric static/freq/optics` |
| 超胞声子、频率及模式分类 | [命令参考](cli_reference.zh-CN.md) | `zstar phonon pre/run/post/irrep` |
| 平面静电势、线剖面与真空电势差 | [静电势](potential_examples.zh-CN.md) | `zstar pot` |
| 可执行文件、MPI/OMP、赝势与轨道 | [配置及资源解析](cli_reference.zh-CN.md) | `zstar config` |
| Shell、Slurm、Torque/PBS 脚本 | [作业 header](job_headers.zh-CN.md) | `zstar bec/phonon/spectra job` |
| 智能体辅助使用 | [Agent Skill](agent_skill.zh-CN.md) | `zstar skill` |

表中的斜杠用于列举子命令，不是可以直接复制运行的完整命令。例如依次执行
`zstar bec pre --stru STRU`、`zstar bec run`、`zstar bec post`。
`job` 只生成脚本，不会自动向调度系统提交任务。

## 按体系选择

| 体系 | 物理维度 | 案例与约定 |
| --- | --- | --- |
| Bulk 晶体 | `--dim 3`，默认 | [三维案例](../examples/3D_Bulk) |
| 法向沿 z 的 Slab | `--dim 2` | [二维案例](../examples/2D_Slab)、[响应归一化](response_conventions.md) |
| 沿 z 周期的 Nanowire | `--dim 1` | [一维教程](one_dimensional_workflow.zh-CN.md)、[一维案例](../examples/1D_Nanowire) |
| Molecule | `--dim 0` | [分子谱学](molecular_spectroscopy.zh-CN.md)、[分子案例](../examples/0D_Molecules) |

`zstar bec pre` 的 `--dim` 表示物理维度；独立的 `zstar phonon pre`
命令中 `--dim "2 2 2"` 表示超胞尺寸，二者不要混用。
分子采用 APT 和极化率，一维、二维分别采用文档定义的线响应、面响应，
不能直接解释为随真空厚度变化的 bulk 介电常数。

## 复现与对比

- [案例总索引](../examples/README.zh-CN.md)：干净 `run/`、已有 `results/` 和 `run.sh`。
- [IR/Raman 案例](../examples/IR_Raman_Spectra/README.zh-CN.md)及
  [静电势案例](../examples/Electrostatic_Potential/README.zh-CN.md)。
- [十体系 BEC/声子效率基准](../examples/Benchmarks/README.zh-CN.md)及
  [四体系 IR/Raman 效率基准](research/unified_spectroscopy_20260906/README.zh-CN.md)。
- [验证记录](validation.zh-CN.md)及[论文质量图片](paper_figures/README.md)。

论文冻结输入请使用 [v0.3.1 源码树](https://github.com/xdzhu/zstar/tree/v0.3.1/examples)。
PyPI 的 wheel 和源码包都不含案例。命令预览、离线重建与重新执行 DFT 是
不同层次的复现；请按各案例 README 检查外部软件、文件及计算资源要求。

**Unified** 指联合响应框架，**Separate** 指原来的独立工作流。
`cartesian` 保留为兼容选项，不再作为旧工作流的名称。历史数据文件名和
基准记录不为统一文字而改动，以保留来源与校验信息。

## 补充接口

使用 [VASP](vasp_bec_zh.md)、[CP2K](cp2k_bec.zh-CN.md)、QE 前，请先查阅
[后端能力](calculator_independent_backends.zh-CN.md)。原生计算路线不会自动
获得 ABACUS 的矩阵复用能力。另见 [High-K/BEC 数据集](highk_bec_database.zh-CN.md)、
[qNEP 导出](qnep_dataset_zh.md)和[输出文件兼容说明](bec_output_compatibility.md)。
