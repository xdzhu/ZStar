# GaN 新计算结果与同泛函文献对照（2026-09-18）

本表仅使用整改后完成的 GaN `production-005`，不复用历史 GaN 数值。
计算来源：`235:/home/zhuxd/abacus/agent-runs/20260918-v2-gan-zno-root-cause/gan/production-005/results/summary.json`。
本次为 ABACUS/PBEsol/LCAO，三维纤锌矿 `P6_3mc`，`z || c`；固定
`±0.005` 工程应变，参考点与十二个正负应变几何均完成 ABACUS 和 PYATB。
报告 proper、relaxed-ion `e`，并由 `d=e(C^E)^-1` 换算 `d`。
表内本次数值保留未施加晶体对称投影的直接拟合结果。

## 文献核查

M.-T. Hoang, J. Yvonnet, A. Mitrushchenkov, G. Chambaud,
“First-principles based multiscale model of piezoelectric nanowires with surface effects”,
*Journal of Applied Physics* **113**, 014309 (2013).
[DOI: 10.1063/1.4773333](https://doi.org/10.1063/1.4773333)。
题名、作者、出版日期与 DOI 经 Crossref DOI 记录核对；数值读取自
[作者上传的原论文全文](https://www.researchgate.net/publication/257973499_First-principles_based_multiscale_model_of_piezoelectric_nanowires_with_surface_effects)，
不是搜索摘要。出版社 DOI 页面本次未能直接读取。
已有 BibTeX 键为 `HoangNanowireBulkPBEsol2013`，不新增重复条目。

- 原文 Table II 的 **GaN bulk / PBESOL** 行：`e31=-0.520`、`e33=0.904`、`e15=-0.373 C/m²`。
- 原文 Table I 的 **GaN bulk / PBESOL** 行：`C11=378.0`、`C12=144.3`、`C13=107.1`、`C33=419.4`、`C55=94.2 GPa`；六方对称下 `C55=C44`。
- 不能把文中的纳米线有效系数或表面系数当作三维体相参考。
- 原文 Eq. (21) 对总 Berry 相位求应变导数后乘晶格向量与逆体积，支持与本次 proper 路径的映射；不能仅凭 Eq. (26) 的简写忽略几何项。
- 原文使用 CRYSTAL Gaussian 基组，单个应变方向采用 `-0.005…0.005` 共十一点、三次多项式拟合。因此匹配泛函不等于匹配全部 Hamiltonian、基组与求导实现；内部弛豫的具体设置仍需补充核查。

## 新增文献值与差异列

差异定义为 `100 × (|本次|-|文献|)/|文献|`；负号表示绝对值偏低，
不是统计误差。剪切分量的绝对值比较不替代完整坐标手性审计。

| 物理量 | 本次 PBEsol | 文献 PBEsol | 差异百分比 |
|---|---:|---:|---:|
| e31 (C/m²) | -0.386014 | -0.520 | -25.77% |
| e33 (C/m²) | 0.665944 | 0.904 | -26.33% |
| e15 (C/m²) | -0.251659 | -0.373 | -32.53% |
| d31 (pC/N) | -1.276382 | -1.605749（由文献 e/C 换算） | -20.51% |
| **d33 (pC/N)** | **2.348732** | **2.975564（由文献 e/C 换算）** | **-21.07%** |
| d15 (pC/N) | -2.735901 | -3.959660（由文献 e/C 换算） | -30.91% |

文献的 `d` 是本报告从同一篇论文、同一泛函的 `e/C` **推导得到**，
不是作者直接报告的数值；`pm/V` 与 `pC/N` 数值相同。六方晶体使用：

```text
den = (C11+C12)*C33 - 2*C13^2
d33 = 1000*((C11+C12)*e33 - 2*C13*e31)/den
d31 = 1000*(C33*e31 - C13*e33)/den
d15 = 1000*e15/C44
```

这里 C 输入 GPa，e 输入 C/m²，输出 d 为 pC/N。亦可由完整六方
6×6 弹性矩阵求逆独立核对。

## 判定

整改后计算闭环完成，但 `e` 与同泛函文献相差约 26–33%，核心 `d33`
相差约 21%。不能称为同泛函文献定量验证通过，也不能改用更接近的
LDA/GGA 数值掩盖差距。上述百分比是文献一致性诊断，不证明偏差的唯一根因。
下一步应定位结构、赝势/轨道基组、极化与内部弛豫定义差异；本次核查不新增
计算任务，不提高统一生产收敛阈值。

## 中心、前向与后向差分：复用已有数据

不新增 SCF 或 PYATB 计算。对同一个参考点、同一组实际序列化工程应变和
branch-matched Cartesian 极化，复用 v2 的 `fit_proper_piezoelectric_response`
与 `fit_elastic_response`。不进行空间群投影；proper 校正始终使用同一个
零应变参考极化。应力采用 ABACUS compression-positive 到 tension-positive
转换，弹性拟合保持与生产收集相同的 major-symmetry 约束。

对于本例实际正负应变（主分量为 ±0.005，其他分量仅有约 1e-16 序列化误差）：

```text
前向：D+ = [P(+h)-P(0)]/h
后向：D- = [P(0)-P(-h)]/h
中心：D0 = [P(+h)-P(-h)]/(2h)
```

实际计算使用完整实际应变向量的线性代数拟合，而非以名义 h 代替。
在光滑响应、对称等间距且噪声可控时，前向/后向截断误差为 O(h)，中心为
O(h²)。独立同方差观测噪声假设下，前向差分的导数噪声标准差是中心的两倍；
实际 SCF/极化误差可能相关，不能将此假设作为本案例的误差估计。

| 物理量 | 中心差分 | 前向差分 | 后向差分 | 前向相对中心的绝对差异 |
|---|---:|---:|---:|---:|
| e31 (C/m²) | -0.386014 | -0.360618 | -0.411411 | 6.579% |
| e33 (C/m²) | 0.665944 | 0.603234 | 0.728655 | 9.417% |
| e15 (C/m²) | -0.251659 | -0.251656 | -0.251661 | 0.00109% |
| d31 (pC/N) | -1.276382 | -1.186040 | -1.366269 | 7.078% |
| **d33 (pC/N)** | **2.348732** | **2.140723** | **2.556492** | **8.856%** |
| d15 (pC/N) | -2.735901 | -2.735882 | -2.735942 | 0.00067% |

差异列采用 `100*abs(前向-中心)/abs(中心)`，与上方文献表的带方向幅值差异
定义不同。每种差分的 d 均由其自身的 e 与 C 换算；不是固定使用中心 C。

| 弹性量 (GPa) | 中心 | 前向 | 后向 |
|---|---:|---:|---:|
| C11 | 346.378294 | 343.725685 | 349.030904 |
| C12 | 127.882222 | 125.620470 | 130.143974 |
| C13 | 93.178665 | 91.508895 | 94.848435 |
| C33 | 384.648996 | 383.147090 | 386.150902 |
| C44 | 91.989957 | 92.030701 | 91.949213 |

隔离弹性换算影响：前向 e 配中心 C 得 `d33=2.1407655 pC/N`，与完整前向
`2.1407230` 很接近，本例 d33 的差异主要来自极化导数而非 C 换算。

审计检查：三种集合的输入秩均为 6，raw e 拟合秩 18/18，major-symmetric C
拟合秩 21/21；重新拟合中心结果与原响应文档的 e/C 分别在 `1e-12 C/m²`
与 `1e-9 GPa` 内一致；`(e_forward+e_backward)/2=e_central` 在 `1e-12 C/m²`
内成立。前向仅含六个非零应变点、后向同理，raw e 为恰定拟合：满秩和小残差
不是单边导数准确性的独立证据。未把三种方法的 d 作简单平均，因为 C 求逆非线性。

结论：**前向可用作单边研究估计，但在本例不宜替换固定生产中心差分**。
前向需要零点与六个正点共 7 个几何，中心需要零点与十二个正负点共 13 个；
这是未对称约化集合的几何数，不是实测加速比。e31/e33 的单边偏差达到约
6.6%/9.4%，剪切 e15 则稳定。正负平均抵消了反号的单边偏差，但当前一组
幅度不能单独区分真实响应曲率、离子弛豫误差、极化积分误差和共同参考点误差。

复现（把 `response_document.json` 指向上述远端结果的本地副本）：

```python
import numpy as np
from zstar.v2.model import ResponseDocument
from zstar.v2.fit import fit_proper_piezoelectric_response, fit_elastic_response
from zstar.v2.units import convert_values

doc = ResponseDocument.read("response_document.json")
strain = doc.quantity("strain_vector")
polar = doc.quantity("polarization_cartesian")
stress = doc.quantity("stress_raw")
assert polar.provenance["branch_matched"] is True
names = strain.provenance["stage_names"]
ref = names.index("reference")
for method in ("central", "forward", "backward"):
    selected = [i for i, name in enumerate(names)
                if name == "reference" or method == "central"
                or (method == "forward" and name.endswith("+"))
                or (method == "backward" and name.endswith("-"))]
    e = fit_proper_piezoelectric_response(
        strain.values[selected], polar.values[selected],
        reference_polarization=polar.values[ref]).proper.proper
    c = fit_elastic_response(
        strain.values[selected], stress.values[selected],
        reference_stress=stress.values[ref],
        stress_sign="compression-positive", enforce_major_symmetry=True).matrix
    c_gpa = convert_values(c, stress.unit, "GPa")
    d = 1000 * e @ np.linalg.inv(c_gpa)
    print(method, e[2, 0], e[2, 2], e[0, 4], d[2, 2])
```
