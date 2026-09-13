# ZStar v2 统一响应理论（第一轮）

**状态：推导基线；未构成稳定 API 或已验证计算功能**
**分支：`zstar-v2-development`**
**对应调研：** [`v2_literature_review.md`](v2_literature_review.md)

本文把 ZStar v1 已完成的 polarization/BEC/Gamma-force/介电链条放进一个可扩展的
线性响应记号，并明确哪些块可以复用同一组第一性原理任务、哪些块必须增加扰动。
所有导数均在参考结构、坐标和边界条件明确后理解；晶体极化是 Berry branch
意义下的多值量，实际代码必须保存 branch 和 reference。

## 1. 记号、坐标和热力学势

* Cartesian 坐标用右手系 `x,y,z`；晶格矩阵的行向量为 \({\bf a}_1,{\bf a}_2,{\bf a}_3\)。
  原子位移 \(u_{i\beta}\) 是原子 *i* 的 Cartesian 位移，单位 m（实现中可用 Å，
  但在 schema 中必须写换算）。
* 原子索引 `i,j=1..N`，Cartesian 索引 `alpha,beta,gamma=x,y,z`。
* 应变采用小应变对称张量 \(\eta_{\alpha\beta}=\eta_{\beta\alpha}\)。对外接口
  预定工程 Voigt 向量
  \[
  \eta_V=(\eta_{xx},\eta_{yy},\eta_{zz},2\eta_{yz},2\eta_{xz},2\eta_{xy}),
  \]
  应力向量为 \(\sigma_V=(\sigma_{xx},\sigma_{yy},\sigma_{zz},\sigma_{yz},\sigma_{xz},\sigma_{xy})\)。
  这样 \(\sigma: \eta=\sigma_V^T\eta_V\)。任何 tensorial-shear 或 Mandel 约定
  都必须在记录中显式标出，不能只保存 6 个数。
* \(\Omega\) 是参考晶胞体积，
  \(q_e>0\) 是元电荷；\(P\) 单位 C m\(^{-2}\)，
  \(\mathcal E\) 单位 V m\(^{-1}\)，\(F\) 单位 N，
  \(\sigma\) 和 \(C\) 单位 Pa。
* 在零宏观场附近使用电焓
  \[
  \mathcal H(u,\eta,\mathcal E)=E_{\rm BO}(u,\eta)-\Omega\mathcal E_\alpha P_\alpha(u,\eta,\mathcal E).
  \]
  电子介电的二阶项包含在 \(P(\mathcal E)\) 中。导数下标 `E`、`D`、`eta`、`sigma`
  分别表示固定宏观电场、电位移、应变或应力；`u` 表示固定内部坐标。

## 2. BEC（Born effective charge）

定义为
\[
Z^{*}_{i,\alpha\beta}
 =\frac{\Omega}{q_e}
  \left.\frac{\partial P_\alpha}{\partial u_{i\beta}}\right|_{\mathcal E,\eta}
 =\frac{1}{q_e}
  \left.\frac{\partial F_{i\beta}}{\partial \mathcal E_\alpha}\right|_{u,\eta}.
\]

第二个等式来自 \(F_{i\beta}=-\partial \mathcal H/\partial u_{i\beta}\) 和 Maxwell
互易关系。\(Z^*\) 的数值单位为 \(q_e\)（通常写作 `e`），第一指标是极化/电场
方向，第二指标是原子位移/力方向；若后端输出相反顺序，adapter 必须记录轴变换。

位移必须是单个原子、单个 Cartesian 向量，且保存实际序列化后的 \(\Delta u\)，不
用名义步长替代。电中性晶体满足 acoustic sum rule
\(\sum_i Z^*_{i,\alpha\beta}=0\)，但数值输出应同时保留 raw 和投影后结果。

### 2.1 周期性和低维边界

在 3D bulk，Berry polarization 和上式使用完整 \(\Omega\)。在 2D slab，周期方向
设为 \(x,y\)，真空法向为 \(z\)：

* 周期方向可定义 sheet polarization \(P^{2D}_{\alpha}=L_zP^{3D}_{\alpha}\)，
  单位 C m\(^{-1}\)，并用面积 \(A\) 写成
  \(Z^*=A/q_e\,\partial P^{2D}/\partial u\)，与体积表达式等价；
* 面外偶极必须由实空间电荷密度（或等价的开放边界方法）得到，不能把含任意真空
  高度的 Berry 体极化直接当成 intrinsic 面外响应；
* `dimensionality=2` 时电场、应变和应力的开放方向必须在边界元数据中注明。

对于非正交 slab，不能把第三个晶格矢量的长度直接当作 (L_z)。若周期面由
(a_1,a_2) 张成、
(\hat n=(a_1\times a_2)/|a_1\times a_2|)，则应使用垂直高度
(h=|a_3\cdot\hat n|=\Omega/|a_1\times a_2|)，并对极化作面内投影：
\[
 P^{2D}_{\parallel}=\left(I-\hat n\hat n^T\right)P^{3D}h .
\]
`normalize_polarization` 显式保存这个几何因子、投影和边界条件，返回 `C/m`；
它不会把开放方向分量伪装成本征 sheet 响应。对应地，1D 只投影到周期轴并乘以
(A_\perp=\Omega/|a_\parallel|)，返回 `C`；0D 必须直接使用分子偶极而不是体积极化。

在 1D wire，周期轴为 \(z\)，横截面积 \(A_\perp\) 只是归一化参考：
\(P^{1D}_z=A_\perp P^{3D}_z\) 的单位是 C，横向 dipole/force 响应需用开放边界
电荷密度；不能使用真空稀释的横向 Berry 值。对分子（`dim=0`），没有晶体周期
polarization quantum；可定义的是原子极化张量 APT（单位 e）和分子偶极/极化率，
不能把 APT 命名为周期晶体 BEC，也不能自动定义 bulk e 或 C。

## 3. 压电张量与应变诱导极化

固定内部坐标的 proper 压电张量为
\[
e^{(0)}_{\alpha\mu}
 =\left.\frac{\partial P_\alpha}{\partial \eta_\mu}\right|_{u,\mathcal E},
\]
单位 C m\(^{-2}\)。\(\mu\) 是上述工程 Voigt 分量；例如
\(e_{\alpha 4}=\partial P_\alpha/\partial(2\eta_{yz})\)。

Berry 极化的直接有限差分会混入晶胞体积变化、坐标旋转和 polarization quantum 的
branch 选择，得到的是 improper quantity。v2 的 `proper` 结果必须：

1. 以同一 reference cell 和连续 Berry branch 比较 \(P(+\eta)\) 与 \(P(-\eta)\)；
2. 记录形变矩阵 \(h'=(I+\eta)h\) 和取向变换；
3. 按 Vanderbilt 的 proper 定义从几何项中扣除/保留所需修正；
4. 在输出中同时给出 raw/improper、proper、branch quantum 和修正项。

Vanderbilt 的直接关系为

\[
 \widetilde c_{ijk}=c_{ijk}+\delta_{jk}P_i-\delta_{ij}P_k,
\]

其中 \(c_{ijk}=\partial P_i/\partial\epsilon_{jk}\) 允许先把形变写成一般
Cartesian deformation。v2 的应变输入只保留对称的小应变，并使用工程剪切分量，
因此对 \(\mu=(jk)\) 的三个剪切列实际使用

\[
 \widetilde e_{i,(jk)}=e_{i,(jk)}
 +\delta_{jk}P_i-\frac12\left(\delta_{ij}P_k+\delta_{ik}P_j\right),
 \qquad j\ne k,
\]

而法向列为 \(\widetilde e_{i,jj}=e_{i,jj}+P_i-\delta_{ij}P_j\)。这里的
\(P\) 必须是 reference 的 branch-matched Cartesian 极化；不能用任意包裹值，
也不能把修正后的张量写回 raw 数据。`proper_piezoelectric_response` 在研究 API
中显式返回 raw、geometric correction 和 proper 三个矩阵，并拒绝未声明的 Voigt
剪切约定。公式依据 Vanderbilt, *Berry-phase theory of proper piezoelectric
response*, J. Phys. Chem. Solids 61, 147 (2000), DOI
[`10.1016/S0022-3697(99)00273-5`](https://doi.org/10.1016/S0022-3697(99)00273-5)。

### 3.1 极化分支的连续匹配

ABACUS Berry 输出的单个方向是包裹值，不能直接相减。令 \(\mathbf Q\) 的列为周期方向
的 polarization quantum，给定路径上一个已经展开的参考值
\(\mathbf P_{\mathrm{ref}}\) 和新输出 \(\mathbf P_{\mathrm{wrap}}\)，v2 选择

\[
 \mathbf n^*=\underset{\mathbf n\in\mathbb Z^{N_p}}{\operatorname{argmin}}
 \lVert \mathbf P_{\mathrm{ref}}-(\mathbf P_{\mathrm{wrap}}+\mathbf Q\mathbf n)\rVert_2,
 \qquad \mathbf P_{\mathrm{match}}=\mathbf P_{\mathrm{wrap}}+\mathbf Q\mathbf n^* .
\]

实现允许 \(\mathbf Q\) 为非正交的 3×3 基底，也允许 2D/1D 的 3×(N_p) 基底；开放方向
不参与整数平移，无法由量子消除的部分作为 residual 返回。路径展开逐点以上一个
已展开值为参考，记录整数 `branch_shift` 和 residual；超过用户给定阈值时失败，
而不是静默跨越 branch jump。当前代码的 ABACUS parser 只负责值/量子/原始单位，
`match_polarization_branch` 和 `unwrap_polarization_path` 才负责连续性，因此仍不
自动声称自发极化或翻转路径成立。

应变有限差分 ensemble 通常按 `reference, +η, -η` 排列，并不是连续的结构路径。
因此 `match_polarization_ensemble` 将每个样本直接匹配到指定 reference 的已选分支，
同时保存实际应变、整数 branch shift 和 residual；它要求输入已经转换为统一的
Cartesian 极化分量，不能把 `gdir=1,2,3` 的三个标量按文件顺序当作 Cartesian 向量。

内部弛豫后，
\[
e_{\alpha\mu}=e^{(0)}_{\alpha\mu}
 +\frac{q_e}{\Omega}
  \sum_{i\beta}Z^{*}_{i,\alpha\beta}\Lambda_{i\beta\mu},
\]
其中 \(\Lambda\) 在下一节定义。第一项是 electronic/clamped-ion（若离子固定），
第二项是 internal-relaxation contribution；两项必须分别保存。

## 4. 弹性张量、柔顺和机械稳定性

固定电场和内部坐标的弹性张量为
\[
C^{\mathcal E,(0)}_{\mu\nu}
 =\left.\frac{\partial \sigma_\mu}{\partial \eta_\nu}\right|_{\mathcal E,u}
 =\frac{1}{\Omega}
  \left.\frac{\partial^2\mathcal H}{\partial \eta_\mu\partial \eta_\nu}\right|_{\mathcal E,u}.
\]

这里的拉伸应力正号约定为拉伸；若 calculator 输出压缩为正，adapter 必须乘以 -1
并在 provenance 中记录。\(C\) 在能量二阶导数近似下应满足
\(C_{\mu\nu}=C_{\nu\mu}\)；柔顺矩阵 \(S^\mathcal E=(C^\mathcal E)^{-1}\)
单位 Pa\(^{-1}\)，应在投影声学零模/固定边界后求逆。

v2 同时保留独立的总能量曲率检验。对 engineering-Voigt 应变
\(\eta=(\eta_1,\ldots,\eta_6)\)，采用 work-conjugate 展开
\[
 E(\eta)=E_0+\Omega\,\sigma_0^T\eta
       +\tfrac12\Omega\,\eta^T C\eta+O(\eta^3).
\]
因此能量二次拟合中的剪切项使用未加倍的
\(\sigma_{yz},\sigma_{xz},\sigma_{xy}\)，而应变列仍为
\(2\epsilon_{yz},2\epsilon_{xz},2\epsilon_{xy}\)。
`fit_energy_elastic_response` 直接对实际序列化应变向量拟合上述模型，显式返回
\(E_0\)、\(\sigma_0\)、对称 \(C\)、设计矩阵秩和能量残差，并要求声明能量、体积和
输出压力单位。它不替代应力拟合，而是用于检查两条独立路径是否满足
work-conjugacy；若二者不一致，必须先检查应力符号、剪切约定、晶胞体积和有限应变
高阶项，不能只报告其中较“好看”的结果。

机械稳定性检查至少包括：对称化前后最大违例、对称/反对称特征值、最小特征值、
条件数和适用的晶系 Born 稳定性不等式。2D 只对面内应变子空间给出 intrinsic 稳定性；
slab 法向和分子体系不得自动套用 3D bulk 判据。

## 5. 内应变响应及 relaxed-ion 修正

定义内部原子在固定外部应变、零内部力条件下的响应：
\[
\Lambda_{i\beta\mu}
 =\left.\frac{\partial u_{i\beta}}{\partial \eta_\mu}\right|_{F=0,\mathcal E}.
\]

令
\[
\Phi_{i\beta,j\gamma}=\frac{\partial^2E_{\rm BO}}
 {\partial u_{i\beta}\partial u_{j\gamma}},\qquad
\Gamma_{i\beta,\mu}=\frac{\partial^2E_{\rm BO}}
 {\partial u_{i\beta}\partial \eta_\mu}.
\]
平衡条件给出
\[
\Phi\,u+\Gamma\,\eta=0,\qquad
\Lambda=-\Phi^{+}\Gamma,
\]
其中 \(\Phi^+\) 是在去除平移声学零模后的伪逆。代入极化和应力展开得到
\[
e=e^{(0)}+\frac{q_e}{\Omega}Z^*\Lambda,
\qquad
C^{\mathcal E}=C^{\mathcal E,(0)}
 -\frac{1}{\Omega}\Gamma^T\Phi^+\Gamma
 =C^{\mathcal E,(0)}-\frac{1}{\Omega}\Lambda^T\Phi\Lambda.
\]

有限差分得到的原子位移本身仍带有整体平移规范。v2 collector 保留原始 Cartesian
位移，**不**自动减去均值或质量中心；使用者必须显式记录 acoustic gauge 后再进入
relaxed-ion 组合。`remove_acoustic_translation` 提供等权或用户权重的中心约束，
权重选择和约束后的数据应写入 provenance。

因此，relaxed-ion 不是“重新命名 clamped-ion”，而是由 BEC、Gamma IFC、
internal-strain coupling 和 homogeneous-strain response 联合构成。实现时必须保留
固定内部坐标的结构和每个弛豫结构的收敛力阈值。

ABACUS 的离子弛豫日志可能包含多个 `TOTAL-FORCE` 块。v2 collector 保留首块
`forces_initial` 和末块 `forces`：首块只有在它对应 `STRU_INITIAL` 的固定离子应变
结构、且日志顺序得到验证时，才可作为 \(\Gamma=\partial^2E/\partial u\partial\eta\)
的候选观测；末块用于离子收敛和最终结构诊断，不能代替 \(\Gamma\)。块数、首末
最大力和结构路径写入 provenance。若日志不包含可识别的首块，必须停止独立
Gamma 重建，而不是用弛豫终态零力填充。

`fit_strain_force_coupling` 将这些首块力与实际序列化的 engineering-Voigt 应变
配对，拟合
\[
\Gamma=-\frac{\partial F}{\partial\eta},
\]
因为 \(F=-\partial E/\partial u\)。输入可以是 `(stage, atom, cartesian)` 或展平的
`(stage, 3*atom)`，并可显式减去零应变参考力；输出行顺序固定为
`(atom, cartesian)`，数值单位沿用输入力单位。该 API 只完成线性拟合和
rank/residual 诊断，不把首块自动提升为已验证的 Gamma：仍需确认首块与
`STRU_INITIAL` 的对应关系、acoustic sum rule、正负应变配对以及独立 IFC/后端证据。

`Lambda` 的数值必须与长度单位一起保存。对于以 `C/m^2` 返回的实现，体积用
`m^3`，并将 `Lambda` 显式转换为米；计算器输出的 `Angstrom` 数值不能直接代入
`q_e/Omega`。v2 algebra API 使用 `internal_strain_unit` 明确这一转换，默认 `m`
仅为保持无单位合成测试的向后兼容；实际 ABACUS 位移拟合应传入 `angstrom`。

弹性内应变修正还必须闭合能量/长度量纲。若 `Phi` 为 eV/Angstrom²、`Gamma`
为 eV/Angstrom、体积为 Angstrom³，则

```text
Gamma.T @ Phi^+ @ Gamma / Omega  ->  eV/Angstrom^3  ->  GPa (or kbar)
```

`relaxed_elastic` 的 unit-aware 模式要求同时提供 `energy_unit`、`length_unit`、
`volume_unit` 和 `elastic_unit`，并检查体积单位确实是长度单位的三次方；它只转换
最终能量密度，`Lambda` 仍以声明的长度单位返回。省略这些关键词的调用保留为
无单位合成代数模式，不能直接写入真实材料的弹性常数。

声学规范必须单独审计，而不能由伪逆“猜测”修复。令 \(T\) 为三个归一化刚性平移
向量（每个原子的同方向位移为 \(1/\sqrt{N}\)），则输入必须满足
\[
 \|T^T\Phi\|,\ \|\Phi T\| \simeq 0,\qquad T^T\Gamma\simeq 0.
\]
前两项分别检查力常数的左、右 acoustic sum rule，后一项检查每个应变下的净力为零。
`acoustic_sum_rule_diagnostics` 只返回绝对/相对残差和兼容性标志，不对数据作静默投影；
`internal_strain_response(..., check_acoustic=True)` 才会在超出给定容差时拒绝输入。这样
可以区分真实的平移零模、有限 SCF/拟合噪声和错误的原子索引或边界条件。即使 \(\Lambda\)
采用 Moore--Penrose 最小范数解，响应文件仍应保存这些诊断及所用的 acoustic gauge。

为避免把伪逆的最小二乘结果误报为力平衡解，研究 API 另提供
`solve_internal_strain_response`。它在使用同一 SVD 截断求解
`Phi @ Lambda + Gamma = 0` 的同时，返回平衡残差、相对残差、平移规范残差、奇异值和
有效秩。生产门控可以传入 `residual_tolerance`：若 `Gamma` 含有未被 `Phi` 支持的非平移
零模分量，调用会明确失败，并提示检查原子顺序、单位和边界条件。旧的
`internal_strain_response` 仍只返回数值 `Lambda`，以保持研究草案的兼容性；它现在复用
同一求解器，因而不会出现“诊断使用另一套伪逆”的不一致。

还有一个不可省略的参考态条件：relaxed-ion 差分的零应变 reference 必须已经在
同一电场/机械边界下满足内部力平衡（以及所采用边界下的应力条件），并且要记录其
最大残余力、应力和空间群。若 reference 只是未弛豫的单点 SCF，±应变弛豫可能进入
与 reference 不同的内部极小值；此时 `P(+eta)` 与 `P(-eta)` 的中点会出现有限偏移，
且多幅度斜率不收敛。该现象不能解释成大的压电响应，必须先弛豫 reference，再重建
应变集合。`relaxed-ion` 的 preflight 因而至少检查 reference 的力阈值、固定晶胞/
应力边界、离子收敛标记和原子对应关系；不满足时只允许保存诊断数据，不允许写入
正式响应张量。

### 5.1 SCF 阈值与离子收敛

SCF 能量阈值和离子力阈值控制不同层次的误差。较严格的 `scf_thr` 通常会降低密度
未收敛引起的力噪声，因此在相同 `force_thr_ev` 下更容易让离子弛豫真正达到目标；
但它不能替代 `force_thr_ev`、最大位移、应力和结构对应关系的检查，也不能消除有限
应变/位移差分的截断误差。v2 记录两者以及每个阶段的最终最大力：基线可用
`scf_thr=1e-8`，当力残差接近阈值、响应随幅度不稳定或 acoustic/内部应变拟合受噪声
限制时，用同一输入做 `1e-10` paired audit。只有在力、响应斜率和重建残差同时改善时，
才把更严格阈值纳入生产设置；不能仅凭 SCF 迭代数或单次更小能量变化宣称离子收敛。

## 6. e、d、g、h 的热力学关系

以下采用应力 \(T\)、应变 \(S\)、电场 \(E\)、电位移 \(D\) 的矩阵形式，
并以单位体积能量为势：
\[
T=C^E S-e^T E,\qquad D=eS+\epsilon^S E.
\]
这里的 \(S\) 是 strain，不是柔顺矩阵；柔顺矩阵记为 \(s^E=(C^E)^{-1}\)。
对应的四种压电矩阵定义和单位为：

| 符号 | 定义（本项目约定） | SI 单位 |
|---|---|---|
| \(e\) | \( (\partial D/\partial S)_E=-(\partial T/\partial E)_S\) | C m\(^{-2}\) |
| \(d\) | \( (\partial D/\partial T)_E=(\partial S/\partial E)_T=e s^E\) | C N\(^{-1}=m V^{-1}\) |
| \(g\) | \( -(\partial E/\partial T)_D=(\partial S/\partial D)_T=(\epsilon^T)^{-1}d\) | V m N\(^{-1}\) |
| \(h\) | \( -(\partial E/\partial S)_D=-(\partial T/\partial D)_S=(\epsilon^S)^{-1}e\) | V m\(^{-1}\) |

在绝对介电张量（F m\(^{-1}\)）下，互换关系为
\[
e=dC^E,\qquad d=\epsilon^T g,\qquad h=gC^D,\qquad e=h\epsilon^S,
\]
\[
\epsilon^T=\epsilon^S+e\,s^E e^T,
\qquad
C^D=C^E+e^T(\epsilon^S)^{-1}e.
\]
若代码保存相对介电常数 \(\epsilon_r\)，转换为绝对量时必须显式乘 \(\epsilon_0\)。
文献有转置、应力正号和 engineering-shear 因子差异；v2 schema 要保存
`matrix_axes`, `voigt_convention`, `stress_sign`, `electric_boundary`
和 `mechanical_boundary`，并提供 round-trip 检查，而不是猜测约定。

## 7. BEC、力常数、介电与压电的响应重建关系

在同一参考点将 \(\mathcal H\) 二阶展开，位移、应变、电场的混合块可用下表表示。
矩阵的数值因位移用 m/Å、极化用 SI/eÅ 而有单位因子，故实现应由带单位的导数对象
生成，而不是复制一个无量纲的匿名 block matrix：

| 扰动对 | 二阶导数/响应块 | 由何种观测得到 |
|---|---|---|
| `u-u` | \(\Phi_{i\beta,j\gamma}=\partial^2E/\partial u_i\partial u_j\) | force 对 displacement |
| `eta-u` | \(\Gamma_{i\beta,\mu}=\partial^2E/\partial u_i\partial\eta_\mu\) | strain 下 force 或 relaxed displacement |
| `E-u` | \(q_e Z^* = \Omega\,\partial P/\partial u\) | polarization 对 displacement（或 force 对 E） |
| `eta-eta` | \(\Omega C^{(0)}=\partial^2E/\partial\eta^2\) | stress 对 strain 或能量曲率 |
| `E-eta` | \(\Omega e^{(0)}=\Omega\,\partial P/\partial\eta\) | polarization 对 strain（或 stress 对 E） |
| `E-E` | \(\Omega\epsilon^u=\partial^2(-\mathcal H)/\partial E^2\) | finite-field/DFPT electronic response |

这组块可组成同一“响应重建体系”，但并不意味着一组 stage 足以得到全部块：
v1 位移/力/极化 ensemble 只能覆盖 `u-u` 和 `E-u`，应变 stage 才能覆盖 `eta-*`，
而电子 `E-E` 还需要电场响应。

所以 v1 Unified 位移/力/极化集合可以一次拟合 BEC 与 Gamma IFC，并由同一 Gamma
IFC+BEC 进入谐性晶格介电响应和 LO--TO/NAC；要获得 e、C、Lambda 必须新增 strain
任务，要获得 \(\epsilon^u\) 则要有电子电场 DFPT/有限场或相容的 PYATB 结果。任何
缺少混合块的“响应重建”都必须标记 incomplete，而不是填零。

`fit_response_document` 是这一原则的文档级实现：它只从已有
`ResponseDocument` 中存在的 `strain_vector`、branch-matched Cartesian polarization、
`stress_raw`、`forces_initial`/`forces` 和 `internal_displacement` 拟合相应块；缺失
观测不补零。输出 quantity 复制输入的单位、周期轴和后端 provenance，并把
`input_rank/allowed_rank/fit_rank/condition/residual/suggested_input_indices` 写入
diagnostics。`stress_raw` 的 backend-dependent 符号必须由调用者显式提供；该层不执行
proper-piezo 几何修正、acoustic gauge 投影或 `Z*Lambda` relaxed-ion 合成，这些仍是
独立验证门。
当文档声明 `relaxed-ion` 而没有 `forces_initial` 时，结果层会拒绝使用末块
`forces` 拟合 Gamma；末块只能作为离子收敛观测，必须重新收集带可识别首块的日志。

## 8. 有限差分精度和实际扰动向量

对任意参数向量 \(x\) 和观测 \(y(x)\)，单方向中心差分为
\[
\frac{\partial y}{\partial x_a}
 \approx \frac{y(x+\Delta x_+)-y(x+\Delta x_-)}
 {\Delta x_+-\Delta x_-},
\]
其中分母是实际序列化的标量；向量扰动集合 \(U\) 用最小二乘重建
\[
J=\arg\min_J\|UJ-Y\|_W,
\qquad
\operatorname{rank}(U)=n_\text{allowed}.
\]
单边差分截断误差 \(O(h)\)，中心差分截断误差 \(O(h^2)\)；舍入/SCF 噪声约按
\(O(\varepsilon_\text{num}/h)\) 放大。每个响应至少做三个幅度（例如
`0.5h, h, 2h`）并报告斜率、条件数和 residual；SCF 未收敛、reference 未达到
内部平衡、Berry branch 跳变或弛豫不完整时不能把差分误差归因于物理非线性。

正负扰动和对称补全应使用真实 \(\Delta u\)、\(\Delta\eta\)；名义 `distance`
只作为生成建议，不能作为后处理分母。应变 clamped-ion 固定分数坐标，relaxed-ion
在每个 ± strain 重新弛豫内部坐标并检查残余力。

## 9. 适用性边界

* 金属或带隙为零时，静态 Berry polarization、BEC 和常规绝缘体 DFPT 不能直接套用；
  任务应在 preflight 阶段失败并指出需使用金属线性响应/有限频率方案。
* 低对称、极性和微小对称破缺结构必须以实际空间群和 tolerance 为准；不能按化学
  经验把原子视为等价。
* 2D/1D 的 intrinsic sheet/line 归一化与 bulk 介电张量不同；真空高度、表面偶极、
  开放方向边界是结果的一部分。
* 分子可以有 APT、力常数、分子极化率和 Raman 响应，但没有周期晶体 polarization
  quantum、bulk piezoelectric e/d/g/h 或 bulk elastic C 的自动定义。
