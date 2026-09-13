# ZStar v2 文献与软件调研（第一轮）

**状态：研究基线，不是已实现功能声明**
**分支：`zstar-v2-development`**
**核查日期：2026-09-13（Asia/Shanghai）**

本文件是 v2 第一轮的调研基线。它只回答“哪些理论和软件事实已经有依据、哪些
问题仍需验证、下一阶段怎样验证”，不把 roadmap 写成稳定 API，也不改变 v1 的
方法、接口或论文。关键论文的题目、作者、期刊、年份、DOI 和可访问链接同时收录
在 [`v2_literature_sources.bib`](v2_literature_sources.bib)。

## 1. 调研方法和边界

采用以下证据优先级：

1. 原始论文和权威综述（APS、AIP、Elsevier、Nature、同行评议期刊）；
2. 软件的官方手册/官方 wiki（用于核对软件能力，不作为物理理论的唯一来源）；
3. 代码仓库或版本化输入输出（用于确认 ZStar v1 的实际行为）；
4. 搜索结果摘要只用于发现条目，未作为最终理论证据。

DOI 通过出版社 DOI 页面或 Crossref/出版社元数据交叉核对；软件能力以官方文档
的当前页面为准，并要求在运行时再次检查版本。由于软件版本会变化，本文的能力矩阵
不是永久兼容承诺。

明确排除：没有把单个材料的数值当成普适理论；没有把有限温、flexoelectricity、
共振 Raman 或相翻转的研究性代码描述为 v2 稳定功能；没有把 VASP/ABINIT 文档中
“可计算”直接解释为 ZStar 已经实现。

## 2. 理论主线的证据链

### 2.1 现代极化、BEC、介电和 Gamma 声子

King-Smith 与 Vanderbilt 建立了绝热变化下极化差的 Berry-phase 表达式，并以
GaAs 压电张量为例；Resta 的综述说明晶体绝对极化是多值量，物理可观测量是参考态
之间的差分或导数。这两点决定 v2 必须保存 polarization branch、参考结构和路径，
不能把两个未经 branch matching 的极化数直接相减。

Gonze 与 Lee 从总能量对原子位移、电场的二阶导数统一得到动力学矩阵、BEC、电子
介电张量和力常数；这正是 v1 Unified BEC/Gamma-force 结果可以作为 v2 基础的理论
原因。Baroni 等综述进一步将应变响应、宏观电场和高阶响应放入 DFPT 的同一框架。
Ghosez 等说明 BEC 不是静态电荷，而是位移引起的宏观极化/电场引起的力响应，且可
通过 Wannier 中心变化理解其异常值。

因此，v2 的第一性原理数据模型应以一个带边界条件的二阶响应块为核心：

```text
                 atomic u        strain eta        electric E
atomic u         Phi (IFC)       Gamma/Lambda       Z* (BEC)
strain eta       Gamma^T         Omega C           e
electric E       Z*^T            e^T               -Omega epsilon
```

其中不同块的计算扰动并不相同：v1 的位移集合足以同时拟合 BEC 和 Gamma 力常数，
但不能凭空产生应变列或电场列；压电、弹性和内应变至少要增加 homogeneous-strain
任务，电子介电则需要电场 DFPT/有限场或现有 PYATB 电子响应。

### 2.2 压电张量、弹性张量和边界条件

Vanderbilt 的 proper-piezoelectric 论文证明，Berry-phase 极化的多值性使直接对
“绝对极化”做有限差分会产生 branch-dependent 的 improper 响应；实验可比较的
proper 响应必须对晶胞形变和 Berry branch 一并处理。Wu、Vanderbilt、Hamann 系列
工作把位移、应变和电场视为统一的能量扰动，明确指出不同电学/机械边界条件会给出
不同的弹性、介电和压电量。Hamann 等的 metric-tensor formulation 给出 strain
DFPT 和 internal-strain terms 的一致实现路径。

对 v2，必须显式区分：

* `e^(0)`：clamped-ion（固定内部坐标）的 proper 压电张量；
* `e`：relaxed-ion（内部坐标随应变弛豫）的张量；
* `C^E`：固定宏观电场的弹性张量；`C^D`：固定电位移的弹性张量；
* `epsilon^S`：固定应变的介电张量；`epsilon^T`：固定应力的介电张量。

工程应变和 tensorial shear 的因子 2 是最常见的接口错误之一。v2 预定采用
`eta_V=(eta_xx,eta_yy,eta_zz,2 eta_yz,2 eta_xz,2 eta_xy)`，并在每条记录中写明
Voigt/Mandel 约定；不允许用“6 个匿名数”传递应变。

### 2.3 有限差分、有限场和 DFPT

Phonopy 官方 formulation 将有限位移力常数写成位移/力线性拟合并提供空间群、平移
和置换对称化；其 Python API 规定 displacement dataset、force constants 的轴顺序
和对称化行为。VASP 官方线性响应文档明确：`LEPSILON`/DFPT、`LCALCEPS`/有限场、
`IBRION=5/6` 应变有限差分和 `IBRION=7/8` DFPT 的能力不同，且 VASP 当前没有用
`IBRION=7/8` 直接得到弹性应变响应的实现。ABINIT 的 `anaddb`/elastic 文档则明确
要求 internal strain 和 relaxed elastic tensor 才能构造 d、g、h。

研究结论是：v2 的 calculator-neutral 层只规定“扰动、观测、单位、边界条件和误差”，
不假设所有 calculator 都支持同一 perturbation。backend resolver 必须返回能力
矩阵，并在缺能力时给出可执行的替代方案或明确失败。

### 2.4 铁电相、极化分支和翻转

Berry polarization 本质上只在 polarization quantum 意义下确定。Bonini、Vanderbilt
和 Rabe 的 Berry-flux diagonalization 通过把 Berry phase 变化分解为小于 `2 pi` 的
连续增量，说明只凭端点也可在特定“最小演化”假设下选择 branch，但真实实验 switching
路径可能包含成核、畴壁和多个鞍点。HfO2 的 lattice-mode analysis 进一步展示同一
极性端点可有多条路径，且反极性/区边模式可能必须共同翻转。因此 v2 phase/switching
模块必须保存原子对应关系、结构插值、每个 image 的 band gap/对称性/能量和 branch
选择；“两个结构的极化差”不是完整翻转功能。

### 2.5 有限温响应和外部 ML/q-NEP 接口

Zhong、Vanderbilt、Rabe 以及 Waghmare、Rabe 的 effective-Hamiltonian 工作表明，
有限温相变需要局域极化模式、应变、短程/长程相互作用和由第一性原理拟合的能量面，
再用 Monte Carlo/MD 采样；不是在 0 K BEC 上加一个温度标签。Behler–Parrinello 和
Deep Potential 说明 ML 势可把第一性原理能量/力扩展到大规模 MD，但极化、电场和长程
库仑响应需额外的带电/动态电荷模型。因而 v2 只应优先提供统一的能量、力、应力、
极化、BEC 数据导出/回读和统计分析接口；训练平台保持外部工具边界。qNEP 的动态电荷
工作可作为后续接口核查对象，但不作为 v2 第一阶段依赖。

有限温结果必须报告：采样长度、平衡段、自相关时间、有效样本数、温度/压力控制、
统计置信区间，并把 DFT 误差与采样误差分开。

### 2.6 Flexoelectricity

Tagantsev 的经典理论指出 flexoelectricity 与 piezoelectricity 在表面贡献、声波和
静态应变梯度极限上并不等价。Stengel 的 DFPT 工作以长波声学声子为基本扰动，在
`q` 的二阶展开中得到 flexoelectric tensor，并明确“零宏观场”规范和表面终止会影响
可比较的数值。Stengel–Vanderbilt 综述将 bulk、surface、open-circuit 边界和 bending
film 统一讨论。

因此 flexo 在 v2 先做 feasibility study：确定 acoustic-phonon long-wave limit、
电子/离子分量、规范、表面与 slab 真空收敛后再决定代码；直接用大超胞的应变梯度
差分代替长波极限是不被接受的快捷方案。

### 2.7 共振 Raman

Albrecht 从 Kramers–Heisenberg–Dirac/Herzberg–Teller 展开说明共振 Raman 振幅依赖
电子激发态、跃迁偶极和声子坐标导数；这不是在非共振 Raman 中换一个展宽或频率窗口。
Lazzeri–Mauri 的非共振 DFT Raman 只需电子密度矩阵对均匀电场的二阶导数；Venezuela、
Lazzeri、Mauri 的双共振 graphene 计算则显式包含电子-光子、电子-声子、缺陷矩阵元
和电子展宽。v2 因此必须先获得频率依赖复极化率/介电函数、带间跃迁和矩阵元，并记录
光子能量、展宽、偏振和可能的多声子过程；在此之前不提供 `zstar spectra resonant`。

## 3. 软件能力核查（用于路线选择）

以下矩阵是“官方软件能力 + 当前 ZStar v1 实际接口”的交集判断。`✓` 表示已有
可核查路径，`△` 表示软件有相关能力但 ZStar v2 尚未接入或需边界条件验证，`—`
表示本轮不应假设支持。

| 后端/工具 | BEC/介电 | Gamma/IFC | homogeneous strain / elastic | internal strain | finite field | Raman | v2 角色 |
|---|---:|---:|---:|---:|---:|---:|---|
| ABACUS + PYATB（当前 v1） | ✓ | ✓ | △ | △ | △ | ✓（非共振） | v2 首要验证后端；先做有限差分适配 |
| VASP | ✓ `LEPSILON`/`LCALCEPS` | ✓ | ✓ 有限差分；DFPT strain 受限 | ✓ | ✓ | △（非共振/模式差分） | 作为交叉验证，逐项声明功能 |
| CP2K | ✓（分子与部分周期） | ✓ | △ | △ | △ | ✓ 原生分子谱 | 先保留既有 BEC/谱接口 |
| Quantum ESPRESSO | ✓ DFPT/PHonon | ✓ | △（需 `q2r`/`matdyn` 与响应模块） | △ | △ | ✓（PH/epsilon 路径） | 待能力探测后接入 |
| ABINIT + anaddb | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 重要独立参考；不是 v2 默认后端 |
| Phonopy | 读取 BEC/介电、IFC、对称化 | ✓ | — | — | — | 非电子响应 | calculator-neutral 后处理和对称性参考 |

官方能力来源：

* [VASP linear response](https://vasp.at/wiki/Linear_response)、[Born effective charges](https://vasp.at/wiki/index.php/Born_effective_charges) 和 [electric-field response](https://vasp.at/wiki/Electric_field_response_from_density-functional_perturbation_theory)；
* [Phonopy formulation](https://phonopy.github.io/phonopy/formulation.html) 与 [Python API](https://phonopy.github.io/phonopy/phonopy-module.html)；
* [ABINIT elastic tutorial](https://docs.abinit.org/tutorial/elastic/)、[Elastic topic](https://docs.abinit.org/topics/Elastic/) 和 [`anaddb` 的 piezo flags](https://docs.abinit.org/variables/anaddb/)；
* [Quantum ESPRESSO PHonon developer manual](https://www.quantum-espresso.org/wp-content/uploads/2022/03/ph_developer_man.pdf)；
* [ABACUS 官方文档](https://abacus.deepmodeling.com/)；PYATB 的实际命令/输出还必须由运行时能力探测确认。

软件文档的用途是核对输入标签、输出位置和限制；压电、弹性、内应变的定义仍以
原始论文和统一理论文档 [`v2_theory.md`](v2_theory.md) 为准。

### 3.1 Elastool 的参考价值

[ElasTool](https://github.com/zhongliliu/elastool) 是一个以 VASP 为主要计算后端的
GPL-3 Python 工具，目标是自动计算二阶弹性常数和机械性质。其论文明确区分三类
应变集合：OHESS（高效率应变矩阵）、ULICS（线性独立耦合应变）和 ASESS（单分量
应变），并采用 stress--strain 方法；当前仓库还覆盖 2D/3D、有限温/压力及后处理
可视化。实现中应变后可选择固定离子或再做固定晶胞离子弛豫，这一点对 v2 的
clamped-ion/relaxed-ion 对照有直接借鉴意义。

它对 ZStar v2 有三方面参考价值：

1. **采样设计**：把 OHESS/ULICS/ASESS 作为 all-six control、效率基线和任务数
   benchmark，而不是把“6 个方向”写死为唯一方案；这与 v2 的任意空间群 rank
   选择可以互补。
2. **弹性验证**：比较 stress--strain 和 energy--strain、应变幅度、应力精度、
   2D 归一化及高温路径，帮助建立 v2 的误差预算和效率报告。
3. **后处理边界**：它主要输出 (C) 及机械派生量，**不提供 v2 所需的 BEC--IFC--
   \(\Lambda\)--piezo 统一响应块，也不替代 proper/improper、固定 \(E\)/固定 \(D\)
   等电学边界审计**。因此只能借鉴算法和 benchmark 设计，不能直接把代码或其
   VASP-centric 输入层移植为 v2 核心；其 GPL-3 许可证也要求避免未经审查的代码
   复制。

### 3.2 已有成熟压电/机电响应路线

目前最适合作为 v2 科学“参考答案”的不是单独的弹性后处理器，而是能够在同一
二阶响应框架中处理应变、电场、原子位移和力的 DFPT 软件：

| 软件/工作流 | 已核查能力 | 对 ZStar v2 的建议角色 |
|---|---|---|
| **ABINIT + `anaddb`** | `rfstrs`、`piezoflag`、`instrflag`；可由 DDB 后处理 relaxed/clamped-ion 弹性、internal strain、(e,d,g,h)、介电和不同 (E/D) 边界量 | 首选科学 oracle；最完整地覆盖 v2 机电理论，但当前节点尚未发现可执行文件，需先做环境和输入验证 |
| **Quantum ESPRESSO + `ph.x`/`thermo_pw`** | QE/PHonon 提供 BEC、介电、IFC；`thermo_pw` 有 Berry-phase 应变压电、clamped-ion 选项、内部坐标弛豫和弹性常数流程 | 第二独立开源路线；适合验证 v2 的单位、剪切和边界条件，但当前节点需先安装/探测 |
| **VASP + py4vasp / atomate(2)** | VASP 有成熟线性响应 BEC/介电/压电路径；atomate/atomate2 提供标准化高通量输入、解析和 provenance | 实用交叉验证和工作流参考；VASP 本身是非开源商业后端，不能作为“开源算法”来源 |
| **Phonopy** | 有限位移 IFC、空间群/置换对称化和 ASR | 继续复用 v1 的位移/IFC 基线；不是压电计算器 |
| **MechElastic / ElasTool** | 读取 VASP、ABINIT、QE 的 (C_{ij})，机械稳定性和派生模量/可视化 | 只作为弹性结果的独立后处理和表示对照，不承担 piezo 物理定义 |

ABINIT 官方文档明确把 phonon、电场和 strain 作为统一 DFPT 扰动，并由这些混合
响应得到 elastic、internal-strain 和 piezoelectric quantities；其测试套件还覆盖
不同定义的 (e,d,g,h)、固定电场/电位移弹性和 internal-strain。这使它比单纯
stress--strain 工具更适合作为 v2 的理论与数值 oracle。

QE 原生 `ph.x` 的强项是 BEC、介电和声子；`thermo_pw` 则提供更接近完整工作流的
应变 Berry-phase 压电和弹性选项。需要注意二者是“可组合的工具链”，不能把
`ph.x` 单独宣称为完整 (e/d/g/h) 工作流。

Materials Project 的 atomate 工作流是很好的工程参考：其公开生产文档列出
`wf_elastic_constant` 和 `wf_piezoelectric_constant`，并通过标准化 pymatgen 输入、
FireWorks/atomate 任务和解析器保存 provenance；但其底层压电计算使用 VASP，故应
借鉴任务图、失败恢复和数据审计，不应把它当作 calculator-neutral 的物理实现。

### 3.3 给 v2 的明确路线

建议采用“三层参考”而不是复制某一个仓库：

1. **ABACUS/PYATB**：继续作为 v2 首要验证后端；每个几何一次 PYATB，保留 v1 的
   三方向极化和 Unified 位移/力基线。
2. **ABINIT `anaddb`**：作为完整机电张量和边界条件的首选独立 oracle；优先核对
   BEC、IFC、internal strain、(e)、(d)、(g)、(h)、(C^E/C^D)。
3. **QE/thermo_pw 或有许可的 VASP**：作为第二独立数值路线；ElasTool 的 OHESS/
   ULICS/ASESS 用作应变采样效率和 stress--strain benchmark。

具体执行顺序是：先把 Elastool 的三种应变集合做成**外部 benchmark 方案**，不把
其代码并入核心；再用 ABINIT/QE 的 DFPT 输出设计 v2 的 `provenance` 映射；最后
才决定是否实现 VASP/QE/ABINIT adapter。任何后端只有在输入、单位、张量轴、边界
条件、对称性和独立参考均通过后，才能进入 v2 稳定能力矩阵。

这里的“独立参考”不等于每个材料都必须再跑一个电子结构后端。若已有可靠的单晶
实验值、原始第一性原理论文或权威数据库条目，文献/数据库可以直接作为外部数值
锚点；必须同时记录晶体相、温度、坐标/IEEE 取向、Voigt 剪切约定、clamped/relaxed-ion
状态、泛函和不确定度。2026-09-13 的 3C-SiC 审计采用这一策略：Lambrecht 等的
cubic-SiC 研究（PRB 44, 3685, DOI `10.1103/PhysRevB.44.3685`）和 Wang 等的
SiC polytype 研究（PRB 52, 3993, DOI `10.1103/PhysRevB.52.3993`）作为原始文献
锚点，Materials Project 的 elasticity/piezoelectric methodology 作为坐标、稳定性
和拟合流程参考。QE/ABINIT 只保留为未来可选 oracle，不再为满足形式上的“第三个
后端”而启动作业。

## 4. 调研问题拆分和待核查项

| 问题 | 已知依据 | v2 设计决策 | 进入实现前的证据门 |
|---|---|---|---|
| BEC 与 Gamma IFC 是否共用任务 | Gonze–Lee；v1 Unified 实际输出 | 共用位移响应，但应变/电场另列 | 三个扰动幅度、ASR、互易性和独立后端对照 |
| e 的 proper/improper | Vanderbilt 2000 | 保存 branch、晶胞体积/旋转修正和约定 | 立方/极性材料与文献张量对照 |
| e/d/g/h 转换 | Wu–Vanderbilt–Hamann；ABINIT anaddb | 从同一热力学势生成带边界标签的矩阵 | 数值互逆、正定性、单位回算 |
| C 的 relaxed-ion 修正 | Hamann 2005 | `C0 - Lambda^T Phi Lambda/Omega` 并保留 C0 | Hessian 可逆性、声学零模处理 |
| 任意空间群 | spglib/Phonopy + intertwiner 线性代数 | 以表示矩阵和秩判据，不以材料特例硬编码 | P1/Pnma/P6mm/P4mm/cubic 五类测试 |
| 低维归一化 | Resta；现有 v1 `response_conventions.md` | 周期/开放方向分别声明；不把真空稀释量叫本征量 | 真空厚度扫描和边界条件审计 |
| switching branch | King-Smith–Vanderbilt；Bonini 2020 | 端点+插值+连续 branch matching | 每个 image 绝缘性和 polarization quantum |
| finite-T | Zhong–Vanderbilt–Rabe；MLIP 文献 | 只做数据接口和回读，不内置训练平台 | 统计误差/自相关/温度收敛协议 |
| flexo | Tagantsev；Stengel | 先可行性研究，不提前定义稳定 schema | 长波、表面规范和 slab 极限一致 |
| resonant Raman | Albrecht；Venezuela–Lazzeri–Mauri | 先频率依赖电子响应接口研究 | 与已验证电子结构/矩阵元交叉检查 |

## 5. 分阶段调研计划

1. **冻结 v1 基线**：保存本分支起点的 commit、测试结果、现有案例清单和脏工作区
   说明；任何 v2 文件都不得改变现有导入或 CLI 行为。
2. **理论闭环**：完成 [`v2_theory.md`](v2_theory.md)，逐项给出变量、边界、单位、
   轴顺序、proper 修正和失败条件。
3. **对称性算法闭环**：完成 [`v2_symmetry_reduction.md`](v2_symmetry_reduction.md)，
   先用解析/合成响应做 rank/residual 验证，再接真实 calculator。
4. **响应 schema 评审**：在实现前冻结 dataclass/JSON schema 草案，提供 v1 adapter；
   不修改现有 `zstar-response` 1.0 文件。
5. **最小机电原型**：只在 Python API 稳定后设计 `piezo`/`elastic` CLI；先以 ABACUS
   小胞 smoke test 验证应变生成、收集和断点状态。
6. **交叉验证**：优先使用已核验的原始实验/理论文献或权威数据库值核对 tensor、
   单位和边界条件；只有在缺少合适外部锚点、或文献定义不完整时，才启动 VASP、
   ABINIT 或 QE 的独立重算。无论采用哪种路径，都记录取向、定义、任务数、SCF、
   core-hours、wall time、最大误差和 residual。
7. **研究性路线**：phase/switching、finite-T、flexo、resonant Raman 分别过理论和
   证据门，未通过前只保留 roadmap。

## 6. 当前结论（第一轮）

* v1 Unified BEC + Gamma force workflow 可以作为 v2 的响应基础；不需要、也不应在
  v2 重新发明一套位移/力常数框架。
* 压电、弹性和内应变在理论上能与 BEC/IFC 放进同一二阶响应块，但必须增加应变
  扰动，并显式区分 clamped-ion、relaxed-ion 和电学边界。
* 任意空间群的安全抽象是“群表示下的线性约束 + 观测矩阵秩/残差”，而不是固定
  cubic/tetragonal 分量表。
* 2D/1D/slab/molecule 的响应不能自动继承 3D bulk 公式；开放方向、真空、表面和
  分子非周期性必须在 schema 中成为一等元数据。
* 有限温、flexoelectricity、相翻转和共振 Raman 均不满足“改几个 CLI 参数即可
  稳定实现”的条件，本轮只完成理论拆分和验证门设计。
