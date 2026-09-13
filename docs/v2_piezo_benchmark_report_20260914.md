# ZStar v2 机电响应 benchmark（2026-09-14，研究审计）

本报告记录当前分支 `zstar-v2-development` 上的 3D bulk 压电原型结果。它不是
稳定 CLI 或 v2 论文结论：所有数值都带有泛函、晶格、坐标手性、工程 Voigt
约定和 proper/relaxed-ion 标签，且必须通过文献映射和独立后端审计后才能升级。

## 计算协议

ZnO、AlN 使用 wurtzite `P6_3mc` 晶胞（`z || [0001]`），GaAs 使用显式的
8 原子 zinc-blende `F-43m` 晶胞。三者均为 PBEsol、Dojo-NC-FR 8-au LCAO、
100 Ry、`scf_thr=1e-8`、六个工程应变分量各取 `±1e-3`。每个几何只运行一次
PYATB，读取同一输出中的三个 Berry 极化方向；ABACUS 原始应力先从
compression-positive 转为张力正号。

HF 通过 Slurm 运行 32 MPI × 1 OMP，未申请节点独占；235 在已分配的计算节点
内直接运行 40 MPI × 1 OMP，不向 PBS 再提交作业。每个 case root 使用 stage
marker 断点续算，禁止并行启动第二个相同 root。

## 已完成结果

### wurtzite AlN（HF，job 27678427，node148）

参考态最大残余力为 `1.39e-4 eV/Å`，13 个几何和 13 次 PYATB 均完成。proper
压电矩阵的独立分量（C/m²）为

| 分量 | v2 PBEsol/Dojo | 文献锚点 |
|---|---:|---:|
| `e31=e32` | −0.723（x/y 差 `2.8e-4`） | −0.60（Bernardini–Fiorentini–Vanderbilt，LDA） |
| `e33` | 1.696 | 1.46（同上） |
| `e15=e24` | −0.374（坐标手性决定符号） | 该来源未给同一约定的 `e15` |

由同一 proper `e` 和 `C^E` 直接计算 `d=e(C^E)^{-1}`，得到（pm/V = pC/N）
`d31=−2.75`、`d33=6.43`、`d15=−3.33`。这与直接 stress-piezo 文献的
`d31=−2.1`、`d33=5.4`、`d15=2.9`（Bernardini–Fiorentini）在量级上相符，
但 `d15` 的符号必须先统一坐标手性。弹性矩阵正定，最小特征值为 `112.25 GPa`。
proper 压电 fit residual 为 `0.53%`，弹性 residual 为 `0.37%`；因此这是已完成
计算但仍处于 literature-audit gate 的结果。

### zinc-blende GaAs（HF，job 27678336，node139）

13 个几何和 PYATB 任务均完成。`F-43m` 对称相关的剪切系数为
`e14=e25=e36=−0.262715 C/m²`，最大等价分量差约 `1.2e-7 C/m²`；
`C44=56.116 GPa`，由 `eC^{-1}` 得 `d14=−4.682 pm/V`。允许子空间 rank 为
18/18，proper residual `6.8e-5`（相对），弹性 residual `2.5e-3`，弹性矩阵
正定。工程器件文献常用的 GaAs 实验值约 `−0.16 C/m²`，现代 GGA 计算可到
`−0.342 C/m²`；这些值的晶格常数、温度和符号约定不同，不能直接作为唯一目标。

### wurtzite ZnO（235，cu17）

原始 `force_thr=1e-3 eV/Å` 生产审计已完成，但六方禁止分量未达到验收门：
`e15` 的 xz/yz 分量分别为 `−0.393/−0.478 C/m²`，proper fit residual 约
`17%`，弹性 residual 约 `4.6%`。这不是可接受的最终材料结论。四个剪切几何以
`force_thr=1e-4 eV/Å` 的独立审计显示 xz 分量变为 `−0.472 C/m²`，与 yz 分量
一致，说明主因是离子弛豫精度而非把 `e33` 当成 `d33` 或 PYATB 三方向读取错误。
当前正在用同一阈值重跑完整 12 个应变几何；完成后才决定是否纳入正式 ZnO 表。

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

AlN 和 GaAs 已完成“计算闭环 + 内部 rank/residual/稳定性检查”，尚未完成独立
后端交叉计算和全部文献约定映射；ZnO 尚未通过 residual gate。故当前不能开放
稳定的 `zstar piezo` 用户入口，也不能把这些数值写成 v2 论文的最终普适结论。
