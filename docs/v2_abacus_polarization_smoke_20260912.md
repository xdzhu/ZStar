# ZStar v2 ABACUS Berry 极化 NSCF smoke（2026-09-12）

## 目的与边界

本次任务只验证 ABACUS Berry 极化输出的读取、单位识别和分支量子保存，
不宣称已经得到压电张量、应变诱导极化或铁电自发极化。所有阶段都是 cubic
BaTiO₃ 参考结构的未应变 NSCF 计算；没有把不同结构的包裹极化直接相减。

ABACUS 官方 Berry 文档要求先有 SCF 电荷，再以 `calculation nscf`、
`init_chg file`、`berry_phase 1` 和 `gdir` 计算各方向 Berry 相位，并在输出中
给出带 polarization quantum 的多值结果：[ABACUS Berry phase documentation](https://abacus.deepmodeling.com/en/v3.6.2/advanced/elec_properties/Berry_phase.html)。

## 计算设置

* 结构：cubic BaTiO₃，5 原子 primitive cell；
* 后端：ABACUS v3.10.0，commit `e84abb4`；
* 泛函/基组：PBEsol、LCAO；`ecutwfc=100 Ry`；
* k 点：`9×9×9`（沿用 v2 多幅度应变 smoke 的结构和资产）；
* 任务：同一参考结构的 `gdir=1,2,3` 三个 NSCF 阶段；
* 资源：cu25、cu26，单阶段 1 MPI rank × 1 OpenMP thread；每个节点保持在
  用户授权的 40 核占位资源以内；
* 结果目录（本地审计副本）：
  `D:\Temp\zstar-v2-abacus-polar-results-20260912`；远端运行目录：
  `/home/zhuxd/zstar_v2_smoke_20260912/polar-smoke2`。

第一次尝试在两个方向上因 `INPUT` 含重复 `symmetry` 键而返回 `RC=1`；保留了
失败日志，随后在干净目录中把该键明确设为单个 `symmetry -1` 后重跑。没有覆盖
失败目录，也没有改动用户的 PBS 占位作业。

## 结果与解析审计

每个成功阶段的 `OUT.POLAR/running_nscf.log` 都包含 ABACUS 的三种等价记录：
`(e/Omega).bohr`、`e/bohr^2` 和直接 `C/m^2`。参考胞输出的体积为
`425.901 Bohr^3`。直接 SI 记录和极化量子如下：

| 阶段 | `gdir` | 解析值 (C/m²) | 解析量子 (C/m²) | 原始单位 |
|---|---:|---:|---:|---|
| `polar-a` | 1 | `-0.0000000` | `2.0199409` | `C/m^2` |
| `polar-b` | 2 | `+0.0000000` | `2.0199409` | `C/m^2` |
| `polar-c` | 3 | `-0.0000000` | `2.0199409` | `C/m^2` |

三个阶段 `time.json` 的 ABACUS wall time 分别为 56.9934 s、57.2715 s 和
56.5239 s，总计约 170.79 s（单线程 wall-time；不等同于完整生产计算的
core-hours）。每阶段均以 `exit_code=0` 记录 ABACUS 正常完成的返回码，同时
保存了输入、`running_scf.log`、`running_nscf.log` 和 charge restart。

将本地目录按故意打乱的顺序 `polar-c, polar-a, polar-b` 交给
`collect_abacus_polarization_triplet` 后，collector 仍按 `gdir=1,2,3` 返回
`[-0.0, 0.0, -0.0] C/m²` 和三个 `2.0199409 C/m²` 量子；三条日志路径也被
保留。这验证了目录枚举顺序不会偷偷成为坐标约定。

此外，针对多幅度应变审计的 `reference` SCF stage 运行了
`prepare_abacus_berry_stages` dry-run，生成 `gdir-1/2/3` 三个目录；每个目录都
包含独立 `INPUT/STRU/KPT`、赝势/轨道和 `OUT.POLAR/POLAR-CHARGE-DENSITY.restart`，
并在 manifest 中记录 `executed=false`。这只是任务准备审计，尚未运行应变 Berry
生产阶段。

为验证 dry-run 的目录可直接执行，又将生成的 `gdir-3` 单独上传到 cu26 运行。
ABACUS 原始 `exit_code=0`，wall time 为 57.40 s，解析得到
`gdir=3`、`value=-0.0 C/m²`、`quantum=2.0199409 C/m²` 和 Cartesian tuple
`[-0.0, 0.0, -0.0] C/m²`。外层 PowerShell 包装因 CRLF 在 `exit` 时返回 1，
但该包装问题与 ABACUS 计算结果分开记录，原始日志和 `time.txt` 均已保留。

解析器 `zstar.v2.polarization` 的约束为：

1. 直接 `C/m²` 记录优先于内部单位记录，避免把 `(e/Omega).bohr` 中的 `Omega`
   误当作常数；
2. 只有在日志提供正的 `Volume (Bohr^3)` 时才转换 `(e/Omega).bohr`；
3. 解析结果保留 wrapped value、quantum、原始单位和 `gdir`，不自动选择铁电
   branch；若日志带有括号中的 Cartesian 三元组，也同时保留该三元组及其单位换算；
4. branch 连续性由单独的 `match_polarization_branch`/
   `unwrap_polarization_path` 完成，并可在非周期方向上报告 residual。

本次 smoke 没有应变对、极化路径或 branch matching，因此不能作为 piezoelectric
结果或自发极化结果。后续 Gate C 仍需在明确 proper/improper 定义、参考胞和单位
边界后，增加带正负应变的 Berry 阶段，并与独立后端或高精度参考交叉核对。
