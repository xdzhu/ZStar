# v2 Gamma（应变—固定离子力）审计（2026-09-13）

## 范围

这是在已有 BaTiO3 `P4mm` 共享目录结果上的离线、只读审计，不是稳定 CLI、正式
benchmark 或独立后端验证。它验证新加入的 calculator-neutral
`fit_strain_force_coupling` 是否使用实际序列化应变、首个 `TOTAL-FORCE` 块、零应变
参考力和正确的力符号；不把一次后处理结果提升为已验证的 Gamma/IFC 常数。

## 定义和数据路径

固定离子力采用

\[
F_{i\beta}=-\frac{\partial E_{\rm BO}}{\partial u_{i\beta}},\qquad
\Gamma_{i\beta,\mu}=\frac{\partial^2 E_{\rm BO}}
 {\partial u_{i\beta}\partial\eta_\mu}
 =-\frac{\partial F_{i\beta}}{\partial\eta_\mu}.
\]

拟合输入为 ABACUS relaxed 日志的首个 `TOTAL-FORCE (eV/Angstrom)` 块，先减去
同一 reference 的首块力，再按每个 stage 中实际写回的 engineering-Voigt 应变
向量拟合；输出矩阵行顺序为 `(atom, cartesian)`，单位为 `eV/Angstrom` 每单位
工程应变。末个力块只用于离子收敛诊断，不能用于 Gamma。

数据位于共享目录
`/home/zhuxd/zstar-v2-tbto-relaxed40-20260912/api-sixstrain-20260913`，本地只读
副本位于 `D:\Work\Scratch\zstar-v2-api-audit-20260913`。计算设置为 PBEsol、
ABACUS LCAO、`ecutwfc=100`、`scf_thr=1e-8`、`force_thr_ev=1e-4`，每个应变 stage
使用 `40 MPI x 1 OpenMP`。这里没有重新提交大任务，也没有用三次 ABACUS NSCF
替代 v1 已有的单次 PYATB 三方向极化读取。

## 多幅度结果

| 数据集 | 应变幅度 | 拟合秩/允许秩 | 最大拟合残差 (eV/Å) | RMS (eV/Å) | `max|Gamma|` (eV/Å) | 首块数量（12 stages） |
|---|---:|---:|---:|---:|---:|---|
| `amp-0005` | `5e-4` | 90 / 90 | `3.23503e-5` | `5.162996e-6` | `25.9558232` | 6,6,6,6,6,6,12,12,12,12,1,1 |
| `amp-00025` | `2.5e-4` | 90 / 90 | `8.01180e-6` | `1.299764e-6` | `25.9566648` | 6,6,6,6,5,5,11,11,11,11,1,1 |

两组拟合矩阵的最大差为 `1.36580e-3 eV/Å`，RMS 差为
`1.85499e-4 eV/Å`；相对于最大 Gamma 约为 `5.3e-5`。这说明在本材料、此
后端和已有收敛设置下，减小应变幅度后斜率变化很小；它不是误差条，也不能替代
不同 SCF 阈值、不同力阈值和独立后端的交叉验证。

首块数量随 stage 和幅度不同，尤其剪切 stage 的输出迭代数不同。因此 collector
把块数和首末最大力写入 provenance，并要求后续 Gamma 使用前核对首块与
`STRU_INITIAL` 的对应关系；块数本身不能证明首块已是严格 clamped-ion 结果。

## 与 `-Phi Lambda` 的同后端交叉检查

另一个已有离线结果提供了 `FORCE_CONSTANTS`（`Phi`）和 P4mm 约化位移拟合的
`Lambda`。将 Phonopy 四阶数组按 `(atom_i, cart_i, atom_j, cart_j)` 重排为二维
`Phi` 后，得到：

* `Phi` 对称残差最大 `1.78e-15 eV/Å²`；
* 左、右 acoustic sum rule 残差最大 `3.55e-15 eV/Å²`；
* `-Phi @ Lambda` 最大值 `25.9834492 eV/Å`；
* `amp-0005` Gamma 与 `-Phi @ Lambda` 的最大差 `6.96843e-2 eV/Å`、RMS
  `1.64452e-2 eV/Å`；`amp-00025` 分别为 `6.99930e-2` 和 `1.64891e-2`。

这是同一 ABACUS/PBEsol 数据链中的代数一致性审计，不是独立 calculator 证据。
差异约为 `2.7e-3`（按最大元素计），可能来自 relaxed-force 首块识别、有限应变、
`Lambda` 拟合和 IFC 规范/采样差异；在这些来源被逐一闭合前，不能报告最终
relaxed-ion Gamma 或由它导出的最终压电/弹性常数。

## 结论和下一步门控

1. `fit_strain_force_coupling` 的力符号、参考力减法、实际应变分母和输出轴顺序已由
   synthetic tests 与两组真实多幅度日志共同覆盖。
2. `scf_thr=1e-8` 在当前审计中已产生可重复的首块斜率；更高 SCF 精度可降低力噪声、
   帮助满足 `force_thr_ev`，但仍需同时检查离子收敛标志、最大力、应力和响应斜率。
   `1e-10` 只应作为成对数值审计，不应未经必要性证明成为默认设置。
3. Gate C 仍未通过：还缺首块—`STRU_INITIAL` 的自动对应性证据、独立 IFC/后端、
   stress work-conjugacy 和 acoustic gauge 的最终规范闭合。因此下一步仍是算法和
   物理核查，不是 CLI 或集群分发优化。
