# ZStar v2 计算输入与收敛协议

状态：研究分支 `zstar-v2-development` 的强制生成约束；适用于 3D bulk 的
ABACUS + PYATB 机电响应。它不追溯修改 v1 的已发布案例，也不把下表直接推广到
slab、wire 或分子：低维体系须先确定真空、面内/轴向归一化与机械边界条件。

## 规则优先级

1. 结构空间群、原子映射和任务生成固定 `symprec = 1e-3 Å`。这是结构识别阈值，
   不是拟合残差的数值验收阈值。
2. 参考平衡结构必须先由独立且**与所选 profile 匹配**的 `cell-relax` 得到；不允许把数据库 CIF、
   低精度预弛豫结构或应变结构的 `STRU_ION_D` 直接作为响应参考态。
3. 响应导数必须由**实际序列化的**位移/应变向量计算，采用中心差分；名义步长只
   作为任务生成参数。
4. 切换 cutoff、k 网格、赝势、轨道、泛函、smearing、晶胞表示或收敛阈值后，参考
   结构与全部响应必须重新生成，禁止拼接不同 Hamiltonian 的 stage。
5. 任一 failed/non-converged stage 都使相应张量不可接受；保存输入和日志后定位原因，
   不以重复盲投覆盖证据。

## 两级输入矩阵：生产与验证

**对未来用户，计算精度参数固定，不执行每材料的自适应扫描。** verification 只供
ZStar 开发者做幅度、异常分量、cutoff/k-point 和论文冻结前复核；它与 production
使用相同的计算器阈值，只增加对比和诊断，不再使用 `1e-6 eV/Å` 或 `scf_thr=1e-10`
一类超高精度输入。

| 阶段 | ABACUS 类型与目的 | 生产档 | 验证档 | 其他强制项 |
|---|---|---|---|---|
| R0：绝缘与基组预检 | SCF；检查绝缘性、赝势/轨道唯一匹配、cutoff 与 k 网格 | `scf_thr=1e-8` | 同生产档 | `cal_force=1`、`cal_stress=1`；检查 band gap 非零、无异常占据 |
| R1：参考平衡结构 | `cell-relax`；同时弛豫晶胞和离子 | `force_thr_ev=1e-4 eV/Å`；`stress_thr=0.5 kbar`；`scf_thr=1e-8`；`relax_nmax=100` | 同生产档 | `symmetry=1`，`symmetry_prec=0.001`，`cal_force=1`，`cal_stress=1` |
| R2c：clamped-ion 零点 | 在 R1 的已验证 `STRU_ION_D` 上 SCF，供应 clamped-ion 力、应力和 PYATB | `scf_thr=1e-8` | 同生产档 | `cal_force=1`、`cal_stress=1`、`symmetry=1`、`symmetry_prec=0.001` |
| R2r：relaxed-ion 零点 | R1 固定晶胞下仅弛豫内部离子，并在最终几何做 PYATB | `force_thr_ev=1e-4 eV/Å`；`scf_thr=1e-8`；`relax_nmax=100` | 同生产档 | 与 R3r 使用**同一**力与电子收敛档；`symmetry=1`、`symmetry_prec=0.001` |
| R3c：clamped-ion 应变 | 固定原子分数坐标的 ± 应变 SCF | `scf_thr=1e-8` | 同生产档 | `cal_force=1`、`cal_stress=1`、`symmetry=0`、`symmetry_prec=0.001` |
| R3r：relaxed-ion 应变 | 固定已应变晶胞、仅弛豫内部离子的 ± 应变 `relax` | `force_thr_ev=1e-4 eV/Å`；`scf_thr=1e-8`；`relax_nmax=100` | 同生产档 | `cal_force=1`、`cal_stress=1`、`symmetry=0`、`symmetry_prec=0.001` |
| R4：Berry 极化 | 每个已完成几何一次 PYATB polar | 继承 R2/R3 Hamiltonian 和 profile | 同左 | 一次 PYATB 输出同时读取三个 Cartesian 极化方向；禁止为三个方向重复三次 ABACUS NSCF |
| R5：BEC/Γ 声子（v1 基线） | 继续使用 v1 Unified 路径，不重新发明算法 | `scf_thr=1e-8`；中心 ± 位移 | 同生产档 | BEC/IFC 位移默认 `0.01 Å`，以实际序列化位移取差分；不以极小位移放大 SCF 噪声 |

`stress_thr` 的单位为 kbar。它是优化停止门，不是泛函绝对应力误差。生产和验证均采用
ABACUS 默认的 `0.5 kbar`；此前已经以 `0.1 kbar` 收敛的结果是更严格的子集，不需要
因为放宽生产门槛而重跑。ABACUS 对 LCAO
优化的公开建议是 `0.04 eV/Å`；固定的 `1e-4 eV/Å` 已比此严格约 400 倍。
JARVIS 的高通量 DFPT 压电/介电数据集采用全弛豫最大残余力 `0.001 eV/Å`；ZStar
当前统一值比该方法学锚点再严格一个数量级，但不继续追求 `1e-6 eV/Å`。

## 生成器约束与参考结构传递

Python API `prepare_abacus_reference_relaxation` 和私有工具
`tools/prepare_v2_reference_relax.py` 默认生成 `production` R1；传入
`profile="verification"` 才生成高精度审计。生成器拒绝比所选 profile 更松的
`force_thr_ev`、`stress_thr`、`scf_thr` 或 `relax_nmax`。R1 收敛后只能显式提升
其 `OUT.<suffix>/STRU_ION_D` 为 R2c 或 R2r 的 `STRU`。R2r 必须通过
`prepare_abacus_fixed_cell_relaxation` 或
`tools/prepare_v2_fixed_cell_relax.py` 生成：该阶段强制
`calculation=relax`，不会继承或重新执行 `cell-relax`。R2r 收敛后再将其最终结构
提升为 R3r 的 `STRU`。每次提升都必须记录原始路径、输入
hash、最终离子力、最终应力、节点、MPI/OMP 与 runtime。

`prepare_abacus_strain_ensemble` 的 relaxed-ion 输入必须是已提升的 R2r 结构；其
reference 仅在该结构上执行 SCF/PYATB，而每一个 R3r `±` 应变点为
`force_thr_ev=1e-4`、`scf_thr=1e-8`、`relax_nmax=100`；`verification` 使用相同
阈值，只增加结果审计。profile 进入 manifest、ensemble 和任务 provenance；不允许把
生产输入标记成验证计算。生成目录中的 `convergence_profile.txt` 是 HF driver 的硬门：
`ZSTAR_V2_CONVERGENCE_PROFILE` 必须与它一致。
clamped-ion 的 reference 为 R2c 单点；relaxed-ion 的 reference 必须为与 R3r 相同
阈值的 R2r fixed-cell ion relaxation。不得把 R1 cell-relax 输出或 R2c 单点与 R3r
的 polarization 混合使用。

## cutoff、k 网格与应变幅度收敛

能量收敛不足以证明响应导数收敛。针对每个候选赝势/轨道组合，先在 R0--R2 进行
cutoff 和 k 网格阶梯，最终设置必须同时使下列已报告量相对前一阶梯稳定：

| 量 | 推荐稳定性目标 |
|---|---|
| 总能量 | `<=1 meV/atom` |
| 参考力 | 固定使用并验收 `force_thr_ev=1e-4 eV/Å` |
| 应力 | 满足所选 R1 profile；另报告相邻基组阶梯的 stress 差 |
| proper `e` | 每个允许独立分量变化 `<=max(0.02 C/m², 2%)` |
| `C` | 每个独立分量变化 `<=max(2 GPa, 2%)` |
| `d=e(C^E)^{-1}` | 每个报告分量变化 `<=max(0.2 pm/V, 3%)` |

用户侧固定中心工程应变为 **`±0.005`（`±0.5%`）**，不提供用户侧幅度扫描或
“自动选最优幅度”。v2 研发者只在代表性 benchmark 上一次性比较 **`±0.005` 与
`±0.01`**；有限差分弹性文献中 `±0.5%/±1%` 是常见的线性审计组合。若二者的允许独立
`e`、`C`、`d` 分量都落入本协议的张量稳定性目标，固定采用较小的 `±0.005`，以减小
有限差分截断误差。若不一致，不能仅因 `±1%` 信号更大就选择它；该 profile 必须标为
未通过并由维护者区分数值噪声与非线性。普通用户始终只运行 `±0.005` 的完整中心差分
ensemble。

完整六分量采样中，所有方向共享同一个未应变零点，因此 production 是
`1 + 2*6 = 13` 个唯一几何。零点不进入中心斜率的分子，但承担平衡态、极化分支、
绝缘性和参考应力审计，不能省略。研发者把 `±0.01` 与同一零点合并时得到 25 个
唯一几何，并可用

```text
D5 = (4 D_0.005 - D_0.01) / 3
```

估计五级四阶导数。该量只回答固定 `±0.005` 的截断误差是否足够小，不替代生产
中心差分，也不成为用户侧可调“点数”。AlN 资格验证中，`D5` 相对 `±0.005` 的
`e31/e33/e15` 变化分别只有 `0.016%/0.019%/0.0047%`，而 `±0.005` 与 `±0.01`
直接结果的最大关键分量变化为 `d33=0.301%`、`C33=0.214%`，因此冻结 13 几何的
`±0.005` 生产方案。

若某个输入在固定 `±0.5%` 下出现极化 branch 不连续、绝缘性丧失、内部弛豫失败、
rank 缺失或非线性诊断超门，稳定用户工作流应明确报为 **unsupported / research review
required**，而不是悄悄缩小应变并继续给出貌似精确的张量。只有 ZStar 维护者在独立的
研发验证中，才能讨论为新的材料类别增加另一个固定 profile。

## 输出、后处理与接受门

- 每个 R2/R3 stage 必须保存 INPUT、KPT、STRU（以及 R3 的 `STRU_INITIAL` 与
  `STRU_ION_D`）、ABACUS/PYATB 日志、输入 hash 和运行统计。
- 对 3D ABACUS LCAO stage，collector 必须逐个解析
  `OUT.<suffix>/istate.info` 的占据/空态流形并保存 VBM、CBM 与 gap；任一文件缺失、
  不可解析或 gap 小于 `0.01 eV` 都阻止 Berry 极化/压电结果进入收集。该检查复用已
  完成 SCF 的本征值表，不增加为三个极化方向重复的 NSCF 计算。
- 收集时将 ABACUS compression-positive 应力转换为 v2 的 tension-positive
  约定；输出保留原始符号的 provenance。
- `e` 必须标记 proper/improper、clamped/relaxed、单位与工程 Voigt 约定；`d`
  必须标记其来源为 `e(C^E)^{-1}`，不得混同直接 stress-piezo 定义。
- 结构对称性固定由 `symprec=1e-3` 审计；张量投影 residual、forbidden component、
  fit residual 是独立诊断，必须报告而不机械套用 `1e-3` 作为拒绝线。
- 若反演对称使 proper piezo 的 allowed rank 严格为零，不对近零张量使用相对残差
  作接受判据；采用固定的 `max|e| <= 1e-3 C/m^2` 绝对数值噪声门，并同时报告 raw
  tensor、forbidden component 和相对诊断。非零 proper-piezo 允许子空间采用
  `max(0.02 C/m^2, 2% * max|e_projected|)` 混合门，并继续报告未投影张量及相对
  residual；该门是验收诊断，不把投影张量冒充原始计算结果。
- relaxed-ion `internal_strain` 在去除等权整体平移后，采用
  `max(1e-3 Angstrom, 1e-3 * max|Lambda_projected|)` 混合门；绝对下限与固定
  `symprec=1e-3 Angstrom` 一致，同时保留 raw Lambda 和相对投影 residual。
- 只有 rank 完整、力/电子/离子收敛、机械稳定、跨幅度稳定、极化 branch 连续，且与
  `PBEsol → PBE → other-GGA → LDA` 分层理论文献比较完成后，才能标为材料验证结果。

## HF 执行约束

从本协议生效后，所有补算只在 **HF Slurm** 提交；235 的计算节点不再用于 v2。

- 使用 `tools/v2_ref_relax_hf.slurm` 跑 R1，并通过
  `ZSTAR_V2_CONVERGENCE_PROFILE=production|verification` 选择相同 profile；驱动会
  拒绝不满足该档阈值的目录。
- 使用 `tools/v2_piezo_hf.slurm` 跑 R2--R4，并使用相同的 profile；不得将 production
  R1 和 verification R3 混在同一个导数或反过来拼接。
- 默认 `32 MPI × 1 OMP`、非独占节点；以 Slurm 实际分配为准，禁止假定整节点。
- 首先提交 R1 单任务 smoke test；检查 `relaxation is converged`、`STRU_ION_D` 和
  输入 hash 后，才提交其余 stage。一个 case root 同一时刻只允许一个 driver。
- 每个任务的 node、Slurm job id、MPI、OMP、wall time、SCF/ionic iteration、失败
  原因与重启次数写入 `provenance.json`；大体积输出和 scratch 不进入 Git。

旧案例只保留历史可追溯性。其结果必须按本文件的 profile、完整输入 hash 与跨幅度
审计重新分级；不得仅凭较小的 `scf_thr` 数字把旧结果重标为验证级。

## 依据与边界

- [ABACUS 输入文档](https://abacus.deepmodeling.com/en/v3.8.0/advanced/input_files/input-main.html)
  给出 LCAO `force_thr_ev=0.04 eV/Å` 的建议、`stress_thr` 的 kbar 单位和默认
  `0.5 kbar`；ZStar 固定使用 `1e-4 eV/Å`、`0.1 kbar`，不再区分更严格的求解器档。
- [JARVIS 高通量 DFPT 研究](https://doi.org/10.1038/s41524-020-0337-2) 对压电、BEC、
  介电和声子数据采用 `0.001 eV/Å` 的全结构弛豫并对 cutoff/k 网格作材料级收敛，支持
  production R1 的取值和“响应量而非只看能量”的收敛策略。
- [ElasTool](https://doi.org/10.1016/j.cpc.2021.108180) 的价值在于通用、独立的
  应变矩阵组与 rank 思路；它面向 VASP 弹性，不能直接替代 ZStar 的 Berry-phase、proper
  `e` 或内应变验证。其示例的 3--6% 弹性拟合幅度也不应直接搬到压电线性响应。
- [VASP finite-displacement 文档](https://vasp.at/wiki/Phonons_from_finite_differences)
  明确区分两点中心 `±h` (`NFREE=2`) 和四扰动 `±h,±2h` (`NFREE=4`)；这支持把
  多点方案用作截断误差审计，而不是默认增加所有生产任务。
- [ABINIT elastic 教程](https://docs.abinit.org/tutorial/elastic/) 使用正负应变中心
  差分；文献实践同时存在 `0,+h`、三点和五级拟合，因此“别人统一用几个点”没有
  单一答案，ZStar 的选择必须由本体系的幅度证据和固定用户协议共同决定。
- 生产档不是降低科学标准：研发阶段必须用代表体系完成 verification、幅度扫描及匹配
  泛函理论对照；一旦 profile 冻结，用户不重复这些扫描。落在固定 profile 适用范围外的
  输入只能输出 `unsupported/research review required`，不能自适应地产生 benchmark 数值。
