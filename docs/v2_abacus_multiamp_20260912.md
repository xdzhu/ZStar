# ZStar v2 ABACUS 六分量多幅度 clamped-ion 试验（2026-09-12）

**状态：** Gate C 数据收集通过；不是冻结后的弹性 benchmark，也不是最终材料常数。
**分支：** `zstar-v2-development`。
**远程目录：** `/home/zhuxd/zstar_v2_smoke_20260912/multiamp`（共享目录中的临时证据）。

## 计算设置

* 结构：cubic BaTiO₃，5 原子 primitive cell，v2 `spglib` 报告 `Pm-3m`，稳定状态。
* 泛函/基组：PBEsol、ABACUS LCAO、`ecutwfc=100`、`KPT=9 9 9 0 0 0`。
* 扰动：六个工程 Voigt 分量 `(xx, yy, zz, 2yz, 2xz, 2xy)`，幅度
  `±0.001` 和 `±0.003`，另加 reference，共 25 个阶段。
* 每阶段均由生成器写入 `cal_force=1`、`cal_stress=1`；拟合读取实际序列化晶胞向量，
  不使用名义幅度。
* ABACUS：v3.10.0，commit `e84abb4`；每个进程 `OMP_NUM_THREADS=1`，每个节点
  同时只有一个阶段进程，未超过用户授权的 40 核边界。

## 资源和可复现性

* 节点：cu24、cu25、cu26；PBS 作业为用户自己的 40 核占位作业，计算通过节点内直接
  SSH 完成，没有修改或提交新的 PBS 作业。
* 三节点串行阶段队列并行推进；每个阶段 `exit_code=0`。
* SCF：25 个阶段均有 12 行 `E_Harris`，合计 300 行；均出现
  `charge density convergence is achieved`、`TOTAL-FORCE` 和 `TOTAL-STRESS (KBAR)`。
* `time.json` 的阶段总和为 3404.922 s（0.946 core-hour，按实际 1 核进程计）；
  三节点阶段队列的最长串行节点时间约 1230.475 s（20.5 min）。
* 远程输出拉回到临时目录后由
  `collect_abacus_strain_response` 读取；临时结果不提交到 Git。

## v2 拟合审计

`strain_vector` 形状为 `(25, 6)`，输入 rank 为 6；stress 由 3×3 张量转换到
work-conjugate Voigt 顺序。先减去 reference stress，再调用
`fit_elastic_response`：

* 直接使用 `stress_sign="backend-raw"` 会明确失败，而不是静默猜符号；
* 在未约束 36 参数空间拟合时，`fit_rank=36`、`allowed_rank=36`、条件数约为 1；
* 最大残差为 0.1486138 kbar（0.0148614 GPa），RMS 残差为 0.0306040 kbar；
* 应变正负与两个幅度的结果给出近似 cubic 结构，但该事实只作为内部一致性证据。

以 **tension-positive** 假设转换，拟合矩阵（单位 kbar）约为：

```text
[[-3209.36792, -1114.79655, -1114.79655,    0,       0,       0],
 [-1114.79655, -3209.36792, -1114.79655,    0,       0,       0],
 [-1114.79655, -1114.79655, -3209.36792,    0,       0,       0],
 [    0,           0,           0,      -1354.58434, 0,       0],
 [    0,           0,           0,          0,    -1354.58434, 0],
 [    0,           0,           0,          0,       0,    -1354.58433]]
```

若后续独立确认 ABACUS 采用 **compression-positive**，则 tension-positive 结果应整体
翻号，即候选 `(C11, C12, C44) ≈ (320.937, 111.480, 135.458) GPa`。目前两种符号
都保留，不能把任一种写成正式 `C`。

作为数值审计，compression-positive 候选的 6×6 对称矩阵特征值（kbar）为
`(1354.584, 1354.584, 1354.584, 2094.571, 2094.571, 5438.961)`，在 draft
`mechanical_stability` 检查中为正；这只是与稳定性相容的迹象，不替代应力符号核查。

## 结论和限制

本试验证明了 v2 应变生成、实际向量保存、六分量多幅度 ABACUS 任务、force/stress
收集、显式符号门控和 rank/residual 审计可以串联工作；它没有证明最终弹性定义已经
冻结。仍需完成：

1. 通过 ABACUS 官方定义或独立受控算例确认 stress sign、应力单位和有限应变约定；
2. 做 cutoff、k 点、SCF 阈值和应变幅度收敛扫描；
3. 以独立后端或高精度参考矩阵交叉核对，并检查能量二阶导数；
4. 加入 polarization/BEC、relaxed-ion/internal-strain 任务后，才可评估压电张量；
5. 通过这些门控后再设计稳定的 `elastic`/`piezo` CLI。
