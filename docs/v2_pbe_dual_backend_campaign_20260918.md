# PBE 双后端压电验证，2026-09-18

## 科学目标与范围

保留所有 PBEsol 结果，另外计算 ABACUS/PBE 和 VASP/PBE，区分泛函差异、
赝势/基组差异与响应算法差异。统一泛函不是完全相同的 DFT 设置，也不保证
消除系统偏差。只改变 `dft_functional`、不优化 PBE 参考结构，不算合格验证。

| 体系 | 目标相 | VASP PAW-PBE 5.4 元素映射 | 对比资格 |
|---|---|---|---|
| AlN | wurtzite，186 | Al, N | 同相 PBE 理论/数据库参考 |
| GaN | wurtzite，186 | Ga_d, N | 同相 PBE 理论/数据库参考 |
| ZnO | wurtzite，186 | Zn, O | 同相 PBE 理论/数据库参考 |
| PTO | tetragonal，99 | Pb, Ti_pv, O | 必须核对四方极性相、方向与晶格 |
| PZT50/50 | 10 原子 [001] 有序模型，99 | Pb, Ti_pv, Zr_sv, O | 单独报告，不等同于无序陶瓷或任意数据库 PZT |

主要数据库依据：[de Jong et al., Scientific Data 2, 150053 (2015)](
https://doi.org/10.1038/sdata.2015.53)。数据库使用 VASP/PAW/PBE/DFPT。
完整 941 条数据库已通过 matminer 官方镜像取得并核验 SHA256；已找到 AlN、GaN、
ZnO、PTO 的同相完整参考行，PZT 有序模型没有匹配条目。
详见 [完整张量对比报告](v2_pbe_database_comparison_20260918.md)。
其完整 e 张量不等于同时提供配套 C、d；d33 必须使用同一计算的 e 与 C，
或直接采用定义、泛函、相和边界条件匹配的文献 d33。

## 固定计算约束

- ABACUS：复用已核对 UPF 头 `functional="PBE"` 的赝势与已有配套轨道，
  `dft_functional=pbe`，记录赝势 SHA256，重新优化独立参考结构。
- 参考结构：力 1e-4 eV/Å，ABACUS `stress_thr=0.5` kbar，
  `scf_thr=1e-8`，`relax_nmax=100`。不增加超高精度要求。
- VASP：PAW-PBE 5.4；`GGA=PE`、`ENCUT=1000 eV`（数据库参考设置）、
  `PREC=Accurate`、`EDIFF=1e-8 eV`、`EDIFFG=-1e-4 eV/Å`、`NSW=100`、
  `ISIF=3`；Gamma k 网格与对应 ABACUS 输入一致。
  当前没有声称完全复现数据库全部设置或指定数据库条目的 POTCAR 版本。
- VASP 的电子能量阈值与 ABACUS 的 SCF 收敛量定义不同，不因为同写 1e-8
  就宣称精度等价。VASP 的力收敛标记也不能代替残余应力验收。
- spglib/phonopy `symprec=1e-3 Å`；ABACUS 不写 `symmetry_prec` 或
  `symmetry_autoclose`。
- ABACUS 响应计划：中心差分 ±0.5% 工程应变，参考加 12 个几何；实际序列化应变用于差分。
- ABACUS 极化：每个几何只运行一次 PYATB，取得全部三个方向，不做三次 NSCF。
- VASP 第一组独立 e 参考使用 `LEPSILON + IBRION=8` 的电子与离子贡献；
  [官方 DFPT 文档](https://vasp.at/wiki/Electric_field_response_from_density-functional-perturbation_theory)
  确认该能力。DFPT 输入另行准备，不把参考优化输入直接作为 DFPT 输入。
  Γ 力常数/绝缘性与输出完整性必须检查。
- VASP 原生优先支持已经在独立分支 `codex/vasp-native-response` 实现：
  `--piezo` 复用原生 DFPT，`--elastic` 复用原生 IBRION=6/ISIF=3 的 e/C；
  由通过质量门的同次 e/C 推导 d。AlN 已验收结果可直接复用，不重复搭建外部差分默认路线。
  本轮仅检查/复用，未合并该独立分支。
- ABACUS 配套 relaxed-ion C^E 采用固定应变下内部弛豫与应力差分，d=e(C^E)^−1；
  Voigt `(xx,yy,zz,2yz,2xz,2xy)`，应力符号显式转换。d33 单列比较。

## 已执行与待执行：严格区分

> 本节以下队列、PID和参考优化状态是2026-09-18初始快照，不是当前终态。
> 当前四种主验证材料的完整结果见
> [双后端审计](v2_completed_backend_pair_audit_20260919.md)；有序PZT的ABACUS中心
> 差分最终为11/12端点通过，`005+`在100步后未过固定力门，见
> [终态审计](data/v2_pzt_strain005plus_terminal_audit_20260919.json)。

远端独立目录：
`235:/home/zhuxd/abacus/agent-runs/20260918-v2-pbe-dual-backend`。

已生成两后端共十个独立参考优化目录、`cases/campaign.json` 与输入/赝势哈希；
参考优化串行队列已启动在 cu26，**40 MPI × 1 OMP**。
cu24、cu25 在检查时仍有既有任务，因此不占用。用户的 PBS 占位不视为冲突，
但实际运行的计算器进程与 CPU 占用会阻止重叠启动。

本次检查：队列 PID 50888；九个参考任务结束，PZT/ABACUS 仍在优化。
AlN/GaN/ZnO/PTO 的 ABACUS 参考优化及 AlN/VASP 优化通过力、应力与空间群检查，
绝缘性尚需补验。GaN/ZnO/PTO 的 VASP 优化 ZBRENT 失败；PZT/VASP 虽返回零，
但没有优化收敛标记且最终力超标，不能验收。
**这些参考优化不是已经完成的压电张量结果。**
独立原生分支的 AlN/VASP/PBE 已取得合格 e/C/d，完整数据库对比见上述报告。

阶段门：

1. 每个参考结构核对电子/离子收敛、最终力、残余应力、空间群和绝缘性。
2. 通过后生成各后端独立的完整响应计算；失败参考不能被直接提升。
3. 检查 e、C、d 的 rank/residual、张量对称性、C^E 稳定性与单位。
4. 输出 `材料 / 相 / 泛函 / 后端 / e31 / e33 / e15 / d33 / 参考 / 百分偏差`；
   小于噪声尺度或对称禁戒的参考分量报告绝对差，不计算误导性百分比。

参考任务退出码、节点、40×1 参数、耗时和 core-hours 写入每个 R1 的
`runtime_pbe_reference.json`；总执行记录为 `cases/reference_execution.json`。
失败日志与输入原样保留，不盲目重新提交；已有执行标记不会被覆盖。

## 代码与测试

新增仅为研究用准备/执行脚本，不修改正式 CLI 或已有物理算法：

- `tools/prepare_v2_pbe_reference_campaign.py`：全量 PBE 资产核查、隔离目录与双后端输入。
- `tools/run_v2_pbe_references_235.py`：指定节点串行参考优化、占用检查与运行记录。
- `tests/test_v2_pbe_reference_campaign.py`：泛函匹配、原始数据保护、固定参数与资产来源。

新增四项与既有应变、VASP 观察/收集、机电换算测试合计 **49 passed**。
未修改 main、v1 正式论文或发布接口，未发布。
