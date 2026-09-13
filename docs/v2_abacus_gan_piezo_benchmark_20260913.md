# v2 3D GaN 压电验证门：完成结果与结论（研究审计）

日期：2026-09-13；分支：`zstar-v2-development`  
状态：**计算已完成；通过首轮研究审计，但尚未晋级稳定功能**

## 1. 计算范围

本轮只选一个 3D、非中心对称、文献锚点清楚的体系：纤锌矿 GaN，空间群
`P6_3mc`、点群 `6mm`。参考结构 1 个，加上六个工程应变分量的正负扰动 12 个，
共 13 个几何。每个几何只运行一次 PYATB，一次输出 a/b/c 三个方向的 Berry 极化；
没有拆成三次 ABACUS NSCF。

ABACUS 使用 PBEsol/LCAO、`scf_thr=1e-8`、40 MPI × 1 OpenMP。参考结构最大力
`2.20e-4 eV/A`，12 个应变结构离子弛豫全部收敛；总 SCF 迭代数 303。一次
`strain-006+` 的 `shm:dapl` 启动停滞，保存日志后用 `I_MPI_FABRICS=shm` 重跑成功。

## 2. 结果

工程 Voigt 顺序为 `(xx, yy, zz, yz, xz, xy)`。对称约束后的直接（improper）结果：

```text
e31 = e32 = -1.70112 C/m²
e33              =  0.66041 C/m²
e15 = e24        =  0.41026 C/m²
```

按 Vanderbilt 几何项显式校正后的 proper 结果：

```text
e31 = e32 = -0.37206 C/m²
e33              =  0.66041 C/m²
e15 = e24        = -0.25427 C/m²
```

弹性拟合（GPa）为 `C11=348.48, C12=128.24, C13=93.01, C33=386.14,
C44=91.84, C66=110.12`。由 proper `e` 和该 `C` 得
`d31=-1.230 pC/N, d33=2.303 pC/N, d15=-2.769 pC/N`。机器可读结果见
`examples/3D_Bulk/wurtzite_GaN_v2/results/piezo_fit.json`。

## 3. 文献对照

Bernardini、Fiorentini 和 Vanderbilt 的原始 Berry-phase 工作给出 GaN
`e31=-0.49`、`e33=0.73 C/m²`，并区分 clamped-ion 与 internal-strain
贡献（[PRB 56 R10024, DOI:10.1103/PhysRevB.56.R10024](https://doi.org/10.1103/PhysRevB.56.R10024)）。
本次 PBEsol/LCAO proper 结果相对差异约为 24% 和 9.5%，同一数量级，但不能宣称
复现原论文精度。Bernardini 2002 的直接 d 张量工作给出约
`d31=-1.4, d33=2.7, d15=1.8 pC/N`（[arXiv:cond-mat/0202496](https://arxiv.org/abs/cond-mat/0202496)）；
本次 `d31/d33` 接近，`d15` 的符号和数值受剪切符号、proper/improper 及文献 Voigt
约定影响，暂不作通过判定。公开 GaN 资料常用 `e15≈-0.30 C/m²`，本次 proper
`-0.254 C/m²` 相差约 15%，但实验锚点的边界条件仍需逐条核对。

## 4. 结论和闸门判定

1. **算法路径已纠正**：PYATB 的 a/b/c 输出必须按 v1 兼容的晶格基底系数线性组合。
   错误地把它们当作三个单位方向投影，会把本例 `e15` 放大到约 `-1.67 C/m²`；
   该错误已经修复并有单元测试。
2. **首轮结果是物理上可信的候选结果**：`6mm` 的 3 个独立压电分量、`rank=3/3`
   和弹性张量对称性均得到；三个 e 分量与公开 GaN 量级相符。
3. **尚不能称为稳定功能或最终论文结果**：当前只有一个应变幅度，极化拟合相对
   残差约 3.2%，尚未完成 ±0.0005/±0.002 幅度收敛、k 点/截断能收敛、clamped-ion
   对照和独立高精度参考。因此 Gate C 暂记为 **conditional**，不是“全部体系已经
   做完”。
4. 下一步只做本例的最小审计：增加两个应变幅度和 clamped-ion 极化对照，确认
   proper 修正、剪切约定和 `d` 转换；通过后再固化 API/案例格式，之后才考虑第二个体系。

BEC/IFC/Gamma 等仍按 v1 基线继承，不在 v2 重复造轮子。
