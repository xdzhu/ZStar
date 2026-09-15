# ZStar v2 计算输入与收敛协议

状态：研究分支 `zstar-v2-development` 的强制生成约束；适用于 3D bulk 的
ABACUS + PYATB 机电响应。它不追溯修改 v1 的已发布案例，也不把下表直接推广到
slab、wire 或分子：低维体系须先确定真空、面内/轴向归一化与机械边界条件。

## 规则优先级

1. 结构空间群、原子映射和任务生成固定 `symprec = 1e-3 Å`。这是结构识别阈值，
   不是拟合残差的数值验收阈值。
2. 参考平衡结构必须先由独立的高精度 `cell-relax` 得到；不允许把数据库 CIF、
   低精度预弛豫结构或应变结构的 `STRU_ION_D` 直接作为响应参考态。
3. 响应导数必须由**实际序列化的**位移/应变向量计算，采用中心差分；名义步长只
   作为任务生成参数。
4. 切换 cutoff、k 网格、赝势、轨道、泛函、smearing、晶胞表示或收敛阈值后，参考
   结构与全部响应必须重新生成，禁止拼接不同 Hamiltonian 的 stage。
5. 任一 failed/non-converged stage 都使相应张量不可接受；保存输入和日志后定位原因，
   不以重复盲投覆盖证据。

## 强制输入矩阵

| 阶段 | ABACUS 类型与目的 | 强制电子/离子阈值 | 其他强制项 |
|---|---|---|---|
| R0：绝缘与基组预检 | SCF；检查绝缘性、赝势/轨道唯一匹配、cutoff 与 k 网格 | `scf_thr=1e-10` | `cal_force=1`、`cal_stress=1`；检查 band gap 非零、无异常占据 |
| R1：参考平衡结构 | `cell-relax`；同时弛豫晶胞和离子 | `force_thr_ev<=1e-4 eV/Å`；`stress_thr<=0.1 kbar`；`scf_thr<=1e-10`；`relax_nmax>=100` | `symmetry=1`，`symmetry_prec=0.001`，`cal_force=1`，`cal_stress=1` |
| R2：参考响应单点 | 在 R1 的已验证 `STRU_ION_D` 上 SCF，供应力、力和 PYATB | `scf_thr<=1e-10` | `cal_force=1`、`cal_stress=1`、`symmetry=1`、`symmetry_prec=0.001` |
| R3c：clamped-ion 应变 | 固定原子分数坐标的 ± 应变 SCF | `scf_thr<=1e-10` | `cal_force=1`、`cal_stress=1`、`symmetry=0`、`symmetry_prec=0.001` |
| R3r：relaxed-ion 应变 | 固定已应变晶胞、仅弛豫内部离子的 ± 应变 `relax` | `force_thr_ev<=1e-6 eV/Å`；`scf_thr<=1e-10`；`relax_nmax>=100` | `cal_force=1`、`cal_stress=1`、`symmetry=0`、`symmetry_prec=0.001` |
| R4：Berry 极化 | 每个已完成几何一次 PYATB polar | 继承 R2/R3 的 ABACUS Hamiltonian 和 SCF 密度精度 | 一次 PYATB 输出同时读取三个 Cartesian 极化方向；禁止为三个方向重复三次 ABACUS NSCF |
| R5：BEC/Γ 声子（v1 基线） | 继续使用 v1 Unified 路径，不重新发明算法 | `scf_thr<=1e-10`；中心 ± 位移 | BEC/IFC 位移默认 `0.01 Å`，以实际序列化位移取差分；不以极小位移放大 SCF 噪声 |

`stress_thr` 的单位为 kbar。R1 的 `0.1 kbar` 是几何优化数值收敛门，而不是声称
交换关联泛函的绝对应力误差小于 `0.1 kbar`。

## 生成器约束与参考结构传递

Python API `prepare_abacus_reference_relaxation` 和私有工具
`tools/prepare_v2_reference_relax.py` 生成 R1，且拒绝任何较松的
`force_thr_ev`、`stress_thr`、`scf_thr` 或 `relax_nmax`。R1 收敛后只能显式提升
其 `OUT.<suffix>/STRU_ION_D` 为 R2/R3 的 `STRU`；该提升必须记录原始路径、输入
hash、最终离子力、最终应力、节点、MPI/OMP 与 runtime。

`prepare_abacus_strain_ensemble` 的 relaxed-ion 默认值是 `force_thr_ev=1e-6`，
自动写入 `scf_thr=1e-10` 与 `relax_nmax=100`；如果显式给出较松的 SCF 阈值则拒绝。
R3 的 reference 为 R2 单点，不能把 R1 的 cell-relax 输出直接与应变 `relax` 的
polarization 混合使用。

## cutoff、k 网格与应变幅度收敛

能量收敛不足以证明响应导数收敛。针对每个候选赝势/轨道组合，先在 R0--R2 进行
cutoff 和 k 网格阶梯，最终设置必须同时使下列已报告量相对前一阶梯稳定：

| 量 | 推荐稳定性目标 |
|---|---|
| 总能量 | `<=1 meV/atom` |
| 参考力 | `<=1e-4 eV/Å`，并满足 R1 输入门 |
| 应力 | `<=0.1 kbar` 的优化停止条件；另报告相邻基组阶梯的 stress 差 |
| proper `e` | 每个允许独立分量变化 `<=max(0.02 C/m², 2%)` |
| `C` | 每个独立分量变化 `<=max(2 GPa, 2%)` |
| `d=e(C^E)^{-1}` | 每个报告分量变化 `<=max(0.2 pm/V, 3%)` |

默认中心工程应变是 `±1e-3`。接受一个材料常数前，至少额外审计
`±5e-4` 与 `±2e-3`，并报告三个幅度的结果、实际应变、branch shift、rank、
condition number 与拟合残差。只有导数落入上表的稳定区间且残差没有系统性随幅度
增长，`±1e-3` 才能成为生产幅度；否则选择线性区间内信噪比最好的幅度并重新做
完整的正负扰动。

## 输出、后处理与接受门

- 每个 R2/R3 stage 必须保存 INPUT、KPT、STRU（以及 R3 的 `STRU_INITIAL` 与
  `STRU_ION_D`）、ABACUS/PYATB 日志、输入 hash 和运行统计。
- 收集时将 ABACUS compression-positive 应力转换为 v2 的 tension-positive
  约定；输出保留原始符号的 provenance。
- `e` 必须标记 proper/improper、clamped/relaxed、单位与工程 Voigt 约定；`d`
  必须标记其来源为 `e(C^E)^{-1}`，不得混同直接 stress-piezo 定义。
- 结构对称性固定由 `symprec=1e-3` 审计；张量投影 residual、forbidden component、
  fit residual 是独立诊断，必须报告而不机械套用 `1e-3` 作为拒绝线。
- 只有 rank 完整、力/电子/离子收敛、机械稳定、跨幅度稳定、极化 branch 连续，且与
  `PBEsol → PBE → other-GGA → LDA` 分层理论文献比较完成后，才能标为材料验证结果。

## HF 执行约束

从本协议生效后，所有补算只在 **HF Slurm** 提交；235 的计算节点不再用于 v2。

- 使用 `tools/v2_ref_relax_hf.slurm` 跑 R1；该驱动会拒绝不满足 R1 强制输入的目录。
- 使用 `tools/v2_piezo_hf.slurm` 跑 R2--R4；该驱动会拒绝 reference 不是
  `scf_thr<=1e-10`、或 relaxed 应变不是
  `force_thr_ev<=1e-6`/`scf_thr<=1e-10`/`relax_nmax>=100` 的目录。
- 默认 `32 MPI × 1 OMP`、非独占节点；以 Slurm 实际分配为准，禁止假定整节点。
- 首先提交 R1 单任务 smoke test；检查 `relaxation is converged`、`STRU_ION_D` 和
  输入 hash 后，才提交其余 stage。一个 case root 同一时刻只允许一个 driver。
- 每个任务的 node、Slurm job id、MPI、OMP、wall time、SCF/ionic iteration、失败
  原因与重启次数写入 `provenance.json`；大体积输出和 scratch 不进入 Git。

旧案例中较松的 `scf_thr=1e-8`、reference `force_thr=1e-3` 或 strained
`force_thr=1e-5` 只保留历史可追溯性，不能用于本协议之后的定量 benchmark。
