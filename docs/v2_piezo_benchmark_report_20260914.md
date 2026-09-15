# ZStar v2 机电响应 benchmark（2026-09-14，研究审计）

本报告记录当前分支 `zstar-v2-development` 上的 3D bulk 压电原型结果。它不是
稳定 CLI 或 v2 论文结论：所有数值都带有泛函、晶格、坐标手性、工程 Voigt
约定和 proper/relaxed-ion 标签，且必须通过文献映射和独立后端审计后才能升级。

## 计算协议

ZnO、AlN 使用 wurtzite `P6_3mc` 晶胞（`z || [0001]`），GaAs 使用显式的
8 原子 zinc-blende `F-43m` 晶胞。三者均为 PBEsol、Dojo-NC-FR 8-au LCAO、
100 Ry、`scf_thr=1e-8`、六个工程应变分量各取 `±1e-3`。初始案例的
relaxed-ion 输入使用 `force_thr_ev=1e-3 eV/Å`；随后 AlN 的 12 个 strained
stage 明确改为 `1e-5 eV/Å` 并重新计算，ZnO 的同阈值审计也已完成。参考结构仍按
各自记录的 reference-equilibrium gate 单独检查，不能把 stage 阈值倒写成参考态
阈值。每个几何只运行一次 PYATB，读取同一输出中的三个 Berry
极化方向；ABACUS 原始应力先从 compression-positive 转为张力正号。

HF 通过 Slurm 运行 32 MPI × 1 OMP，未申请节点独占；235 在已分配的计算节点
内直接运行 40 MPI × 1 OMP，不向 PBS 再提交作业。每个 case root 使用 stage
marker 断点续算，禁止并行启动第二个相同 root。

## 已完成结果

### wurtzite AlN（HF，reference job 27678427；audit job 27682276）

参考态沿用 job 27678427（node148），最大残余力为 `1.39e-4 eV/Å`；12 个 strained
stage 在 job 27682276（node268，32 MPI × 1 OMP）中以 `force_thr_ev=1e-5 eV/Å`
重新弛豫，最终最大力均不超过 `9.276e-6 eV/Å`，且每个 stage 只运行一次 PYATB。
proper
压电矩阵的独立分量（C/m²）为

| 分量 | v2 PBEsol/Dojo | 文献锚点 |
|---|---:|---:|
| `e31=e32` | −0.693（x/y 差 `2.8e-4`） | −0.60（Bernardini–Fiorentini–Vanderbilt，LDA） |
| `e33` | 1.696 | 1.46（同上） |
| `e15=e24` | −0.374（坐标手性决定符号） | 该来源未给同一约定的 `e15` |

由同一 proper `e` 和 `C^E` 直接计算 `d=e(C^E)^{-1}`，得到（pm/V = pC/N）
`d31=−2.66`、`d33=6.36`、`d15=−3.33`。这与直接 stress-piezo 文献的
`d31=−2.1`、`d33=5.4`、`d15=2.9`（Bernardini–Fiorentini）在量级上相符，
但 `d15` 的符号必须先统一坐标手性。弹性矩阵正定，最小特征值为 `112.25 GPa`。
proper 压电 fit residual 为 `0.497%`，弹性 residual 为 `0.255%`。收集阶段和准备
阶段统一采用 v2 固定 `symprec=1e-3`，最终参考结构识别为 `P6_3mc`。因此 AlN
仍是“计算完成、待响应 residual 与文献审计”，不能把另一套未被 v2 采用的严格
容差结果误写成真实相变。共同不变度量 Cartesian 表示修正后，Gamma
force--strain intertwiner 已通过。tighter-force 审计使 internal-strain 的对称投影
相对残差从 `3.19%` 降至 `0.0415%`，proper、elastic、Gamma 和 internal-strain
四类张量现在均进入 `P6_3mc` 允许子空间的 `1e-3` gate。与此同时 raw
internal-displacement fit residual 从 `1.09%` 变为 `2.59%`；这项中心差分
线性/噪声诊断不能被对称投影抹去，仍需应变幅度审计。因此 AlN 的内部 G3 仍标为
conditional，而不是直接升级为最终材料常数。

### zinc-blende GaAs（HF，job 27678336，node139）

13 个几何和 PYATB 任务均完成。`F-43m` 对称相关的剪切系数为
`e14=e25=e36=−0.262715 C/m²`，最大等价分量差约 `1.2e-7 C/m²`；
`C44=56.116 GPa`，由 `eC^{-1}` 得 `d14=−4.682 pm/V`。允许子空间 rank 为
18/18，proper residual `6.8e-5`（相对），弹性 residual `2.5e-3`，弹性矩阵
正定。工程器件文献常用的 GaAs 实验值约 `−0.16 C/m²`，现代 GGA 计算可到
`−0.342 C/m²`；这些值的晶格常数、温度和符号约定不同，不能直接作为唯一目标。
受限基底审计的 proper 投影残差为 `9.11e-7 C/m²`（相对 `5.9e-6`），elastic
投影残差为 `3.07e-6 kbar`，与 `F-43m` 观测空间群一致。

### wurtzite ZnO（235，cu17、cu24--cu26）

12 个 strained geometry 在用户 PBS 保留的 cu17、cu24--cu26 上完成，且每个几何
只运行一次 PYATB（共 13 次，40 MPI × 1 OMP ABACUS）。用于收集的 PYATB 均采用
Dojo Zn/O 的 `valence_e=20 6`；早期误写 `12 6` 的 PYATB 输出已隔离、未参与张量。
proper 结果为 `e31(x)=−0.61522`、`e31(y)=−0.61535`、`e33=1.26810`、
`e15(xz)=−0.47693`、`e15(yz)=−0.47701 C/m²`；由 `e(C^E)^{-1}` 得
`d31=−5.969/−5.961`、`d33=12.464`、`d15=−11.964/−11.957 pm/V`。弹性矩阵
正定，最小特征值 `39.863 GPa`。

不过，当前仍不能把 ZnO 标记为最终通过：proper/elastic/Gamma 的受限投影残差分别
为 `5.781e-4`、`2.414e-4`、`5.820e-4`，但 internal-strain 仍为 `1.188e-2`；
proper raw fit 的绝对最大残差为 `1.49e-4 C/m²`（相对归一化残差 `14.65%`），
internal-displacement raw fit 为 `11.53%`。一次 `yz` shear 的 `1e-6` 定向审计中
负点收敛而正点两次均在 50 ionic steps 后失败，故整对严格输出归档并排除。
准备阶段记录的 `P6_3mc` 与最终参考结构在统一的 `symprec=1e-3` operational
tolerance 下相符。该结果仍归档为“完成计算、待响应 residual 与文献审计”，不
作为普适材料结论。受限 proper 基底投影残差为
`7.58e-4 C/m²`（相对 `5.78e-4`），elastic 投影残差为 `0.495 kbar`；这说明
共同不变度量 Cartesian 表示修正后 Gamma force--strain 已通过，但 internal-strain
仍有约 1.19% 投影残差。更严格的应变弛豫已明显改善，但不能抵消 proper fit residual
和 internal-strain 尚未通过的问题。

## 文献锚点

* Bernardini、Fiorentini、Vanderbilt, *Phys. Rev. B* **56**, R10024 (1997),
  DOI [10.1103/PhysRevB.56.R10024](https://doi.org/10.1103/PhysRevB.56.R10024)：AlN/GaN
  Berry-phase `e` 与自发极化。
* Bernardini、Fiorentini, *First-principles calculation of the piezoelectric
  tensor d of III-V nitrides* (2002), [arXiv:cond-mat/0202496](https://arxiv.org/abs/cond-mat/0202496)：
  AlN/GaN 的直接和间接 `d` 比较。
* Dal Corso 等, *Phys. Rev. B* **50**, 10715 (1994),
  DOI [10.1103/PhysRevB.50.10715](https://doi.org/10.1103/PhysRevB.50.10715)：ZnO
  的 Berry-phase `e`（LDA/实验结构定义）。
* McKitterick 等, *Phys. Rev. B* **28**, 7384 (1983),
  DOI [10.1103/PhysRevB.28.7384](https://doi.org/10.1103/PhysRevB.28.7384)：GaAs
  的第一性原理压电与介电响应。

## 当前 gate

GaAs 已完成“计算闭环 + 内部 rank/residual/稳定性检查”，但仍需完整文献约定映射；
AlN 的 tighter-force 闭环已使四类 symmetry projection 全部通过，但 raw
internal-displacement fit 仍待幅度审计。ZnO 已完成 `1e-5` 同阈值闭环但仍有
internal-strain/原始拟合残差。故当前不能
开放稳定的 `zstar piezo` 用户入口，也不能把这些数值写成 v2 论文的最终普适结论。
