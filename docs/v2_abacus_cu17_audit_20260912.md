# ZStar v2：cu17 独立极化与内部弛豫审计（2026-09-12）

状态：研究性审计；不构成 BaTiO₃ 的发表基准，也不替代完整 relaxed-ion 张量。
分支：`zstar-v2-development`。所有正式工作目录与本审计目录位于共享 scratch
`/home/zhuxd/zstar-v2-tbto-relaxed40-20260912`，未写入 `main`、未上传发布。

## 目的

cu17 在 PBS、负载和 `pgrep` 检查后确认空闲。为核查收敛误差和内部离子弛豫效应，
对同一个 `strain-001-` 应变几何分别做：

1. formal runner 已完成的 relaxed 终态（`OUT.POLAR/STRU_ION_D`）单点 SCF；
2. formal stage 保留的原始应变结构（`strain-001-/STRU_INITIAL`）固定离子 SCF。

两次均为一次 ABACUS 40-rank 计算，随后各运行一次 PYATB `POLARIZATION`。PYATB
一次运行内部完成 a/b/c 三个 Berry loop；没有拆成三个 ABACUS NSCF 任务。两次早期
误复制终态的输出整体移入 `wrong-final` 归档，只保留作审计痕迹，不参与结果。

## 软件、输入和资源

* ABACUS `3.10.0-LTS`，commit `e84abb4`：
  `/home/zhuxd/Software/abacus/INSTALL/3.10.0-LTS/bin/abacus`。
* Intel MPI：`/home/zhuxd/intel/oneapi/mpi/2021.9.0/bin/mpirun`。
* PYATB 输入生成器：`/home/zhuxd/Software/anaconda3/envs/icu/bin/pyatb_input`；
  Python：同一 `icu` 环境；精度适配器为共享目录的 `pyatb_precision.py`，不改动
  PYATB 数值 kernel，仅把 polarization writer 扩展到 16 位并保留哈希。
* PBEsol、LCAO、`ecutwfc=100 Ry`、Gamma `9×9×9`、`scf_thr=1e-8`、
  `scf_nmax=200`；赝势/轨道与 formal `strain-001-` 完全相同。
* 每次：`40 MPI × 1 OpenMP`，`OMP_NUM_THREADS=MKL_NUM_THREADS=OPENBLAS_NUM_THREADS=1`，
  `I_MPI_PIN=1`，节点 `cu17`。没有修改 PBS 占位或抢占其他用户作业。

代表性命令（路径为共享目录中的审计副本）：

```bash
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 I_MPI_PIN=1
mpirun -np 40 /home/zhuxd/Software/abacus/INSTALL/3.10.0-LTS/bin/abacus
pyatb_input -i . -o pyatb_clamped_original --polar --valence '10 12 6'
mpirun -np 40 /home/zhuxd/Software/anaconda3/envs/icu/bin/python \
  /home/zhuxd/zstar-v2-tbto-relaxed40-20260912/pyatb_precision.py
```

## 结果

| 几何 | ABACUS 时间 | `P_a` (C/m²) | `P_b` (C/m²) | `P_c` (C/m²) |
|---|---:|---:|---:|---:|
| relaxed `OUT.POLAR/STRU_ION_D` | 123 s | `6.45126176896e-08` | `5.91542549349e-08` | `0.395023978915` |
| clamped 原始 `STRU_INITIAL` | 123 s | `6.47732564442e-08` | `5.96164275675e-08` | `0.348768835474` |
| relaxed − clamped | — | `-2.60638754638e-10` | `-4.62172632565e-10` | `0.0462551434409` |

两次 PYATB 输出均包含完整 a/b/c 行和 `zstar_precision.json`。`P_c` 的明显变化
说明内部离子弛豫在此应变点不可忽略；这只是一个分量、一个幅度的差分审计，尚未
拟合 `Λ_{iβμ}` 或 relaxed-ion `e`，也没有据此宣称材料常数。绝缘性、Berry branch
连续性、stress sign/单位和多幅度线性收敛仍由 Gate C 负责。

## 可追溯性

* relaxed 审计目录：
  `/home/zhuxd/zstar-v2-tbto-relaxed40-20260912/audit-cu17-001minus-20260912`。
* clamped 审计目录：
  `/home/zhuxd/zstar-v2-tbto-relaxed40-20260912/audit-cu17-001minus-clamped-20260912`。
* 输入哈希：`INPUT=6844b1b0fe1f4ecf140d14f1d97f91dbeac9c4ee7527901157a79751888504b8`；
  `STRU_INITIAL=f62c4ab4bd30ba4b9bdcfa40bdca7c0ff8666b706cf96cd3ac922cfcb89fea25`；
  `KPT=36ed6ce38df591bb0c19c8c77ffed5527ff49d2e7eeaf3143785518b201a0085`。
* 正确 clamped `polarization.dat` SHA256：
  `c08d911b7d03d3fa083444341d5a0ce5c0e2175c6db384041099909b954f5c52`。
* 资源日志、输出文件、运行命令和被排除的 `wrong-final` 归档均保留在上述共享目录；
  仓库只提交本摘要，不提交赝势、轨道或大体积缓存。

