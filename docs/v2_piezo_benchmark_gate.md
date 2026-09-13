# v2 压电正式 benchmark 门：wurtzite GaN

**状态：候选案例已冻结，计算结果尚未产生；不构成材料结论。**

本文件把 v2 的第一个正式压电验证目标限制为一个 3D、绝缘、非中心对称且
晶体对称性简单但非立方的体系：wurtzite GaN（空间群 `P6_3mc`，点群 `6mm`）。
这不是要求把仓库中的每个材料都重算一遍，而是为算法建立一个定义可核查的
最小闭环。SiC 继续作为中心对称弹性控制，不参与压电数值比较；BaTiO3 的
现有 P4mm 目录继续作为内部算法审计 fixture，不升级为正式材料 benchmark。

## 1. 为什么先选 GaN

* `6mm` 的独立压电应力分量只有 `e15=e24`、`e31=e32` 和 `e33`，足以检验
  对称性约化、六分量工程应变、剪切约定和三方向 Berry 极化重建。
* 原始文献同时给出了 Berry-phase `e`、Born 电荷、内部参数响应，以及由
  弹性张量转换得到的 `d`，可作为定义映射的数值锚点。
* 另一篇原始论文直接计算了 stress-piezoelectric `d`，并列出 GGA/LDA、
  间接 `d=eC^{-1}` 和多个实验值，能够检查 v2 的 `e↔d` 代数与边界条件说明。
* 计算单胞只有两个原子，适合先做一个完整的 40 MPI × 1 OpenMP 端到端闭环，
  不需要为“增加案例数量”启动一批无关的大型作业。

## 2. 外部锚点（定义匹配后使用）

Bernardini、Fiorentini 和 Vanderbilt 的 Berry-phase 研究给出 GaN wurtzite
的理论值（单位 `C/m^2`）：`e33=0.73`、`e31=-0.49`；文中同时讨论
clamped-ion 与 internal-strain 分解，并明确使用 Voigt 应变约定。其表格中的
数值属于该文献的 LDA/赝势/平衡结构定义，不能直接当作 ABACUS/PBEsol 的目标值，
只能在记录泛函、结构、轴向和 proper/improper 约定后比较。

Bernardini 和 Fiorentini 的直接应力响应研究给出 GaN 的 stress-piezoelectric
系数（单位 `pm/V = pC/N`）：

| 分量 | GGA 直接 | LDA 直接 | 间接值（由 e 与 C） | 实验范围/条目 |
|---|---:|---:|---:|---:|
| `d31=d32` | -1.4 | -1.5 | -1.2 / -1.4 | 文中实验换算值需注明受限外延条件 |
| `d33` | 2.7 | 2.7 | 2.4 / 2.6 | 2.6、3.1、3.7 |
| `d15=d24` | 1.8 | 3.3 | — | 3.1 |

这些值的实验比较存在外延夹持、自由悬空转换和基底影响；原论文明确指出
偏差通常可达约 4--30%。因此 v2 的 benchmark 报告必须同时列出定义和不确定性，
不能只给一个“误差百分比”。

## 3. v2 计算定义

1. 结构：wurtzite primitive cell，笛卡尔 `z || [0001]`；使用完整非正交六方
   晶胞，不把 `a/b/c` 极化标量直接当作笛卡尔分量。
2. 参考态：先做固定晶胞内部坐标弛豫并记录残余力/应力；若参考态不是零应力，
   只能报告“给定结构的导数”，不得称为平衡材料常数。
3. 扰动：六个工程 Voigt 应变分量各取 `+/- eta`，每个几何只运行一次 PYATB，
   从同一个 `polarization.dat` 读取 `a,b,c` 三个方向，再显式解晶格方向矩阵得到
   Cartesian `P`。
4. 两条响应：
   * clamped-ion：固定分数坐标，拟合 raw/improper `dP/deta`；
   * relaxed-ion：固定晶胞弛豫离子，另行记录 `Lambda`、力阈值和最终结构，随后
     计算 proper 修正和内部应变贡献。
5. 电子结构：必须逐 stage 记录 band-gap/绝缘性；任何金属化 stage 不能进入
   Berry 极化拟合。
6. 收敛：正式首轮使用 `scf_thr=1e-8`；只有当极化差或应力残差接近验收阈值时，
   才增加 `1e-10` 精度审计，不以更小阈值代替定义核查。
7. 完备性：`6mm` 允许空间的 rank、拟合 residual、奇异值和被禁止分量均需保存；
   禁止分量必须区分“群论严格为零”和“数值接近零”。

## 4. Gate C 验收条件

正式材料结论只有在以下条件全部满足后才允许写入案例摘要或论文：

* 参考态、所有 `+/-` 实际应变向量、输入哈希和三方向 PYATB 输出齐全；
* 六方 `6mm` 对称性重建 rank 完整，允许分量 residual 在预先声明的阈值内；
* clamped-ion、relaxed-ion、proper/improper 均带单位、Voigt、轴向和边界标签；
* `e -> d` 与直接 stress/strain 定义的回算在数值误差内一致；
* 至少与一组原始理论锚点和一组实验/数据库条目逐分量比较，并解释差异来源；
* 至少一个扰动幅度和一次 `scf_thr` 精度审计通过；
* provenance 记录节点、40 MPI × 1 OpenMP、SCF 次数、core-hours、wall time、
  失败/重启次数和输出哈希；
* 结果仍需经过 v1 回归测试，不能修改 v1 接口或正式论文。

在这些条件满足前，本案例的状态只能是 `research_audit`，不能开放稳定
`zstar piezo` CLI，也不能声称“GaN 压电常数已被 ZStar 验证”。

## 5. 原始来源

* F. Bernardini, V. Fiorentini, and D. Vanderbilt, “Spontaneous polarization and
  piezoelectric constants of III-V nitrides,” *Physical Review B* **56**, R10024
  (1997), DOI [10.1103/PhysRevB.56.R10024](https://doi.org/10.1103/PhysRevB.56.R10024).
* F. Bernardini and V. Fiorentini, “First-principles calculation of the piezoelectric
  tensor d of III-V nitrides,” arXiv:cond-mat/0202496 (submitted 2002), open manuscript
  [arXiv:cond-mat/0202496](https://arxiv.org/abs/cond-mat/0202496).
* N. Nakamura, H. Ogi, and M. Hirao, “Elastic, anelastic, and piezoelectric
  coefficients of GaN,” *Journal of Applied Physics* **111**, 013509 (2012), DOI
  [10.1063/1.3674271](https://doi.org/10.1063/1.3674271). This is an additional
  experimental source; its sign and boundary convention must be checked before use.

