# PBE 跨档案 C/d 参考：2026-09-19

## 结论和适用边界

de Jong 的941条压电档案直接报告proper relaxed-ion e，不直接报告d。
另一个1181条弹性档案包含AlN/mp-661、GaN/mp-804、ZnO/mp-2133的完整C；
没有PTO/mp-20459。因此可以为前三者构造**有条件的跨档案d参考**，
不能将其写成“数据库直接报告的d33”或“同一计算来源的精确配对d”。
全部结构和设置差异保留；本审计不改变任何native d质量门。

两篇原始论文分别为
[A database to enable discovery and design of piezoelectric materials, de Jong et al., Scientific Data 2, 150053 (2015), DOI10.1038/sdata.2015.53](https://perssongroup.lbl.gov/papers/sdata2015-piezoprops.pdf)
和
[Charting the complete elastic properties of inorganic crystalline compounds, de Jong et al., Scientific Data 2, 150009 (2015), DOI10.1038/sdata.2015.9](https://perssongroup.lbl.gov/papers/sdata2015-elasticprops.pdf)。
两者使用VASP/PAW/PBE、IEEE张量约定；压电论文设置1000 eV/2000 pra，
弹性论文使用700 eV，本次三条弹性记录kpoint_density均为7000 pra。
记录级原始INCAR及PAW哈希不可得，不宣称完全相同输入。

## 数据核查

2026-09-19核对[matminer官方元数据](https://raw.githubusercontent.com/hackingmaterials/matminer/main/src/matminer/datasets/dataset_metadata.json)，
读取既有本地冻结gzip缓存，不调用MP API，不查询凭证、不重下载全档案、不运行DFT。

| 档案 | 核对数量 | SHA256 |
|---|---:|---|
| piezoelectric_tensor | 941/941 | dc9d04836f7f91ecb4ef6dc23e42468571be857f0fccafdfb51a5a40f19db898 |
| elastic_tensor_2015 | 1181/1181 | 8c3b342f75da7e7baa1b769b59554485fd647f4cb1da9318d0d1ba3b3b838183 |

按唯一material_id选择，再核对有序三维周期结构、组成、SG186及共同+a/+c坐标方向。
spglib固定symprec=1e-3 Å、angle_tolerance=5°，没有扫描阈值或标准化/优化结构。
显式读取IEEE elastic_tensor，而非任意POSCAR方向的原始C。
严格JSON拒绝重复键及非有限值，并限制压缩/展开大小；各档案数量和哈希均与元数据一致。
数据URL、软件实际版本、输入输出哈希及解析警告记录在审计JSON中。

## 完整矩阵关系和单位

采用工程应变η=(εxx,εyy,εzz,2εyz,2εxz,2εxy)，
应力σ=(σxx,σyy,σzz,σyz,σxz,σxy)。固定E的relaxed-ion C满足σ=C^Eη，
proper e满足δP=eη。因此d=e(C^E)^−1，映射普通应力Voigt，而不是工程应力。
完整3×6与6×6矩阵求解；不能以e33/C33代替包含横向耦合的d33。
e单位C/m²，C由GPa显式转Pa，d为C/N；乘10^12转pC/N，等价pm/V。
要求参考C有限、major-symmetric且正定，不先静默投影C以制造可逆性。

## 几何与极性畴审计

物种对应、同元素置换及共同原点平移后，使用完整三维周期晶格距离。
另做全局结构反演诊断，但**保留压电档案e的原始畴和符号**。
C是反演偶的四阶张量；该诊断可解释来源结构的相反极性取向，
不消除两个计算几何及数值设置不同的事实。

| 材料 | C档案相对e档案体积差 | 直接对应最大距离 Å | 反演后对应最大距离 Å |
|---|---:|---:|---:|
| AlN | −0.054797% | 0.000903052 | 1.188858 |
| GaN | −0.127601% | 1.291588 | 0.000041920 |
| ZnO | −0.193519% | 1.282531 | 0.000551909 |

GaN/ZnO的原始结构直接对应并非同极性取向，反演后接近；AlN直接对应接近。
三个结构均不满足文件序列化精度下的完全同几何。
1e-6的文件几何/坐标方向诊断只处理文本序列化，不改变spglib1e-3 Å或生产力阈值。

## d33 单独比较

参考值由跨档案e、C组合求得，并非数据库原生d。单位pC/N（=pm/V）。
有符号差异为100×(计算−跨档案参考)/abs(跨档案参考)。

| 材料/后端 | 本次/已验收d33 | 跨档案PBE参考d33 | 有符号差异 |
|---|---:|---:|---:|
| AlN/ABACUS | 4.975410 | 5.342677 | −6.87% |
| AlN/VASP（已验收） | 5.324396 | 5.342677 | −0.34% |
| GaN/ABACUS | 1.872239 | 1.720637 | +8.81% |
| GaN/VASP | 未验收，不填 | 1.720637 | — |
| ZnO/ABACUS | 9.666372 | 9.273189 | +4.24% |
| ZnO/VASP | 未验收，不填 | 9.273189 | — |
| PTO/ABACUS | 49.084674 | 没有配对C，不推断 | — |
| PTO/VASP | 未验收，不填 | 没有配对C，不推断 | — |

保留ZnO/ABACUS辅助Lambda对称性警告；该列d来自独立直接应变e/C。
不将诊断代数native d填入未通过门限的行，不用参考接近来覆盖质量警告。

## 完整 C 比较

以跨档案IEEE C为参考；以下Frobenius比仅指所注明工程Voigt矩阵，
不是任意坐标旋转下不变的四阶张量范数。

| 材料/后端 | 完整C Voigt Frobenius差 | 最大分量绝对差 GPa |
|---|---:|---:|
| AlN/ABACUS | 1.4136% | 4.6674 |
| AlN/VASP | 0.4574% | 1.7187 |
| GaN/ABACUS | 3.0811% | 12.6487 |
| GaN/VASP | 0.9176% | 3.4833 |
| ZnO/ABACUS | 4.9203% | 12.6715 |
| ZnO/VASP | 2.1387% | 5.7648 |

这些差异是确定性的比较指标，不是置信区间、标准不确定度或普适精度保证。
原始数据没有所需不确定度/协方差，故standard_uncertainty=null；不虚构误差条。

## 复现与测试

研究脚本`tools/audit_v2_pbe_reference_pairing.py`的输入为两份冻结缓存、
`.codex-output/matminer_dataset_metadata_20260919.json`及已有`comparison.json`。
最新独占输出为
`outputs/pbe_database_comparison_20260918/cross_archive_pbe_reference_pairing_PTO_collected_20260919.json`；
保留先前输出，不覆写其来源哈希。完整C差矩阵与完整参考d也在JSON中。

测试`tests/test_v2_pbe_reference_pairing.py`包含完整三维六方张量求解/剪切/单位、
四原子周期结构原点/置换/反演/晶格改变、不可逆/不稳定/非major C和严格JSON负例。
单位静态审计0 findings、0 suppressed；该启发式检查不能代替物理单位和公式推导。
本轮完整本地回归638 passed、4345 warnings（主要既有spglib/Phonopy弃用警告），32.92 s；
包括上述8项新参考审计测试。当前环境并非所声明最低依赖版本的发布验证环境，
所以这不构成支持范围或发布资格证明。
脚本只是研究参考审计，不新增API、CLI或发布功能，不调整原生科学门或生产精度。
