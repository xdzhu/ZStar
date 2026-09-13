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

### 3.1 高精度剪切审计

针对 `±0.0005` 下异常的 `e15`，又完成了只包含 `strain-005±` 的定向审计：
`scf_thr=1e-10`、`force_thr_ev=1e-4`，负点在 cu25、正点在 cu24，各使用一个
`40 MPI × 1 OpenMP` ABACUS 任务；每个几何仍只运行一次 PYATB 并回读三方向极化。
按每个几何自身的非正交晶格基底转换后，raw/improper 中心差分为
`e15=+0.41040 C/m²`；施加 reference-branch proper 几何项 `-0.66453 C/m²` 后，
得到 `e15=-0.25413 C/m²`、`C44=91.84 GPa`、`d15=-2.767 pC/N`，与
`±0.001/±0.002` 的稳定值一致。因此原 `±0.0005` 异常判定为收敛噪声，而非
晶格基底变换或压电公式错误。原始输入/输出摘要见
`examples/3D_Bulk/wurtzite_GaN_v2/results/high_precision_shear_audit.json`。

## 4. 结论和闸门判定

1. **算法路径已纠正**：PYATB 的 a/b/c 输出必须按 v1 兼容的晶格基底系数线性组合。
   错误地把它们当作三个单位方向投影，会把本例 `e15` 放大到约 `-1.67 C/m²`；
   该错误已经修复并有单元测试。
2. **首轮结果是物理上可信的候选结果**：`6mm` 的 3 个独立压电分量、`rank=3/3`
   和弹性张量对称性均得到；三个 e 分量与公开 GaN 量级相符。
3. **尚不能称为稳定功能或最终论文结果**：幅度审计、clamped-ion 对照和定向高精度
   剪切审计已经完成；但极化拟合残差、单一泛函/后端和独立后端核对仍未满足生产门。
   因此 Gate C 仍为 **conditional**，不是“全部体系已经做完”。
4. 下一步先完成本例的响应文档回读、完整单位/边界条件审计和独立参考核对；通过后
   才固化稳定 API/案例格式，之后再考虑第二个 3D 体系。

BEC/IFC/Gamma 等仍按 v1 基线继承，不在 v2 重复造轮子。
