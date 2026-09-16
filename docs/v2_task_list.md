# ZStar v2 优先级任务清单

状态：`zstar-v2-development` 研究分支；2026-09-16 更新。

本清单是 v2 的唯一执行顺序。它以 v1 已完成的 Unified
symmetry-adapted finite-displacement framework 为基础，不修改 `main`、v1
正式论文或已发布接口。任务只有在前置门通过后才能开始；未通过时记录失败原因，
而不是通过增加命令、材料或后端掩盖问题。

## 共同完成定义

每个计算/算法任务至少应保留：输入哈希、实际序列化扰动向量、结构/对称性、单位与
坐标约定、ABACUS/PYATB 输出、Slurm job/node/MPI/OMP/wall time、重启/失败记录，
以及 rank、raw residual、symmetry-projection residual。材料结论还必须经过匹配
泛函的理论文献比较（PBEsol → PBE → other-GGA → LDA）。

`symprec=1e-3 Å` 只用于结构空间群与原子映射；它不是张量 residual 的放行阈值。

## P0 — 已完成：AlN 固定精度与幅度资格验证

目标：判定目前的 wurtzite AlN PBEsol/Dojo/100 Ry/8×8×6 研究闭环能否冻结为第一个
v2 机电验证案例，并同时审计固定生产应变 `±0.5%` 的适用性。

| 子任务 | 状态 | 进入条件 | 交付物/退出条件 |
|---|---|---|---|
| A0.1 R1 参考平衡结构 | **完成**；HF job `27697265`，node14，32 MPI × 1 OMP，813 s | 固定输入协议 | `cell-relax` 已收敛并产生 `STRU_ION_D`；今后固定 `force_thr=1e-4 eV/Å`、`stress_thr=0.1 kbar`、`scf_thr=1e-8`、`relax_nmax=100` |
| A0.2 `±0.5%` relaxed-ion ensemble | **完成**；最终 HF job `27705472`，32 MPI × 1 OMP，6437 s | A0.1 | 13 个几何均完成 ABACUS + 每几何一次 PYATB 三分量极化；最小带隙 4.109 eV；机械稳定 |
| A0.3 `±1%` relaxed-ion ensemble | **完成**；最终 HF job `27705473`，32 MPI × 1 OMP，6284 s | A0.1 | 同 A0.2；最小带隙 4.049 eV；只供研发幅度审计，不成为用户可选参数 |
| A0.4 独立收集与幅度判定 | **完成** | 两组输出完整 | 0.5%/1% 的 `e31/e33/e15` 相差 0.048%/0.057%/0.014%，`d33` 相差 0.301%，关键 `C` 分量相差不超过 0.214%；固定生产幅度保留 `±0.5%` |
| A0.5 文献冻结判定 | **完成：qualified research benchmark** | 数值门通过 | PBEsol 一级对照：`e` 偏差 3.3--10.4%，`C` 偏差 2.5--9.9%；GGA 二级 `d` 偏差 3.6--14.2%。冻结 0.5% 结果，不采用 1% 结果替代生产导数 |

两组已经通过固定 `1e-4 eV/Å` 的物理验收门；现有输出实际曾以错误的开发输入
`force_thr=1e-6 eV/Å`、`scf_thr=1e-10` 运行，该事实保留在 provenance 中，但不再
作为 ZStar v2 的输入或验收标准。结果收集没有重新运行 ABACUS/PYATB。

本轮 HF 共使用 240.702 core-hours。其中 233.476 core-hours 来自不应采用的
`1e-6/1e-10` 输入；这不等于全部科学结果无效。能够明确归因于错误零点流程并重复
提交的 jobs `27705207/27705472/27705473` 合计 **114.498 core-hours**，属于可避免
消耗。剩余“超高精度相对 `1e-4/1e-8` 多花了多少”没有同体系固定精度计时对照，
不得编造数值。后续不为估算这个差额而重算。

## P1 — 当前优先级：机电核心的算法闭合

仅在 P0 产生可审计结果后开始，优先修算法与数据模型，不扩 CLI。

1. 完成完整 3D central-strain collector 的独立复算：raw/improper 与 proper `e`、
   clamped/relaxed 标记、tension-positive stress、engineering-Voigt 转换、
   `C ↔ S ↔ d/g/h` 的显式边界条件。
2. 对所有输出强制实际向量、input hash、单位、Cartesian axes、periodicity、
   ion-state、rank/singular values/raw residual/projection residual 的 schema 审计。
3. 检验 `BEC + Gamma IFC + Lambda` 重建的 internal-strain contribution 与直接
   relaxed-ion 差分的一致性；不重新实现 v1 BEC/IFC 路径。
4. 为 R1 `cell-relax`、R2/R3、PYATB、断点续算、缺失 PP/ORB、非收敛/金属 stage、
   polarization branch、单位与符号各增加回归测试。

**退出门：** 一个 3D 合格案例的 G0--G4 完整证据，核心测试与全部 v1 回归通过；
仍只暴露研究 Python API。

## P2 — 任意空间群的对称性约化资格

目标是减少第一性原理任务而不改变物理定义。

1. 将已写的表示/线性代数方案接到真实 3D strain ensemble；明确哪些 stage 被严格
   省去、哪些只在后处理重建。
2. 用 cubic、tetragonal、hexagonal、orthorhombic、monoclinic/低对称五类结构做
   “全 6 分量参考采样 vs 约化采样”审计；比较完整张量、rank、残差和禁止分量。
3. 覆盖非标准晶胞、微小对称破缺、等价原子映射与退化表示；对 rank-deficient 或
   `symprec=1e-3` 下空间群不稳定输入明确拒绝并回退完整采样。

**退出门：** 每类均有全采样对照，约化重建在预声明误差内且没有将数值近零误写为
对称性禁止。此前，不把 reduction 作为用户默认路径。

## P3 — 最小 3D 压电/弹性原型与跨材料验证

按下面顺序，不并行堆积无关材料：

1. **GaAs：** 先补齐 PBEsol/PBE 理论 `e14` 锚点与轴/手性核对；利用已有内部
   G0--G3 结果判断 G4，而非无目的重算。
2. **ZnO：** 仅针对未闭合的 `e15/C44/internal-strain` 做同协议的严格诊断；未解释
   14.65% raw residual 前，不扩大材料池。
3. **3C-SiC：** 作为中心对称 elastic control；验证压电严格为零与弹性结果，不能
   用它声称压电能力。
4. **tetragonal 极性体系：** 在前述六方/立方控制通过后，选 PbTiO3 或 HfO2 的
   一个已绝缘、文献充分的体系验证低对称/极性情形。
5. **orthorhombic/低对称体系：** 最后只选一个有匹配理论文献的绝缘体，验证一般
   space-group 下的 rank 与 tensor reconstruction。

**退出门：** 至少一个非立方极性体系和一个中心对称 control 的 G0--G4 证据完整；
在此之前，不能宣称已普适验证压电能力，也不能发布稳定 `zstar piezo`/`elastic` CLI。

## P4 — 稳定接口、案例和工程化

前置为 P1--P3 全部通过。届时才：

1. 冻结 calculator-neutral response schema 与 Python API，补迁移/失败说明。
2. 设计并测试 `piezo pre/run/stat/post`、`elastic pre/run/stat/post` CLI；CLI 只
   暴露固定生产 `±0.5%`，验证档和 1% 审计保持维护者接口。
3. 建立可复现案例目录、HF Slurm 模板、provenance 和 benchmark 报告；更新手册及
   Agent Skill，并明确 experimental/stable 状态。
4. 完成 v1/v2 全量回归、运行效率和正确性共同统计；不发布 PyPI 或 GitHub release。

## P5 — 铁电 phase/switching 模块

以 P4 完成的极化/机电核心为前置。先完成参考相配对、结构原子对应、连续 Berry
branch matching、绝缘性门和插值能量/极化路径；NEB 仅在职责边界确定后评估。交付
的是 research API 与可复现小案例，不把两个结构的极化差称为翻转计算。

## P6 — 有限温数据接口研究

先做数据导出/回读与不确定度设计：能量、力、应力、极化、BEC、局域结构及采样
metadata。评估 effective Hamiltonian、外部 ML/q-NEP 与 MD 的参数和统计需求，
不在 ZStar 内建立 ML 训练平台。只有外部模型和误差预算明确后才实现分析接口。

## P7 — flexoelectricity 可行性门

先完成长波定义、strain-gradient/声学响应、电子/离子分解、体相/表面边界、超胞和
二维真空依赖的理论与小型验证。若规范或边界条件不能固定，则保留研究报告而不写代码。

## P8 — 共振 Raman 可行性门

先证实后端可输出频率依赖极化率、电子跃迁/光学矩阵元、展宽与光子能量依赖；建立
相对声子坐标导数与偏振张量验证。非共振 Raman 或仅改变展宽不是此功能的证据。

## P9 — 论文与发布审查

v2 论文只写已通过相应 Gate 的代码、案例和可复现 benchmark。P5--P8 未完成的部分
只列 roadmap。最后才执行 v1/v2 回归、文档/Skill 审计及发布审查；未经明确授权，
不合并 `main`、不上传 PyPI、也不创建 release。

## 暂不开展的事项

- 不为“多后端交叉验证”重复运行 ABINIT/QE/`anaddb`，能以匹配理论文献或数据库
  进行核验的先用其作外部锚点。
- 不在 2D slab、1D wire 或分子上沿用 3D bulk `e/C/d` 定义；先有独立边界与归一化
  理论门。
- 不让单一材料、单一幅度或 symmetry projection 替代跨幅度、raw residual、机械
  稳定性和文献核验。
