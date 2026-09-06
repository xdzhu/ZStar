# 一维链与纳米线工作流

当前默认 Raman 路线见 [Unified 谱学教程](unified_spectroscopy.zh-CN.md)。Sb2S3
复用 BEC 矩阵；留存的 52 次 SCF 模式差分属于独立对照，不是 Unified 的额外要求。

## 投稿案例的 BEC 与效率统计

主要展示 BN(9,0) 纳米管与 Sb2S3 单链。BN 管的 BEC 先逐原子变换至
径向/切向/轴向局域正交坐标，再按元素求平均：B 为 `(0.397, 1.256, 2.745) e`，
N 为 `(-0.474, -1.178, -2.745) e`。不同原子的局域坐标不同，不能直接用局域
分量求和检验电中性；应在共同笛卡尔系中检验。全部张量和局域范围存于
`Nanotube_BN_9_0/results/BEC_comparison/`。

Sb2S3 的代表原子 `(7,8,1,2,3)`，轴向 BEC 分别为
`(4.642, 5.972, -4.101, -3.353, -3.159) e`；将参考原子排序匹配并将其周期
x 轴转至 z 后，B3LYP-D3(BJ) 参考为 `(4.341, 6.135, -3.786, -3.430, -3.260) e`。
完整三组对角分量、全张量和匹配诊断存于 `Nanowire_Sb2S3/results/BEC_comparison/`。
参考为 [Ulian 的公开计算数据集](https://doi.org/10.17632/6tntvw37tr.1)，尚未核实
关联期刊论文。不同泛函及分别优化的结构只能用于比较张量特征与数值尺度，不能
称为同方法精度验证。谱学图同样保留原始参考曲线和 Raman 相对强度差异。

| 体系 | Separate BEC SCF | 独立声子 SCF | Separate 合计 | Unified 联合 SCF |
|---|---:|---:|---:|---:|
| BN(9,0) | 61 | 56 | 117 | 57 |
| Sb2S3 | 31 | 20 | 51 | 21 |

| 体系 | Separate BEC 核时 | 独立声子核时 | Separate 总核时 | Unified 联合核时 | 加速比 |
|---|---:|---:|---:|---:|---:|
| BN(9,0) | 140.05 | 130.36 | 270.41 | 125.04 | 2.16 |
| Sb2S3 | 23.74 | 17.93 | 41.67 | 18.95 | 2.20 |

BEC 计入一次参考 SCF，额外声子不重复计算参考。Unified 的极化与力来自同一次
计算，不能将其 BEC 与声子机时重复相加。SCF 指独立自洽计算，不是电子迭代步数。
Sb2S3 的旧方案 BEC 和独立声子分别为 23.74、17.93 核时，合计 41.67，
对比 Unified 的 18.95 核时，实测加速 2.20 倍、节省 54.5%。BN(9,0) 节省
53.8%。cu20 上一次独立力任务中断，完整耗时未记录；已保留现场并在 cu25
完成剩余阶段。表中仅统计成功计算，不是包括中断损耗的总计费量。加速比不是
任务数比值的代称。
结构优化与额外 Raman 位移不计入此 BEC+声子 benchmark。

Sb2S3 两套方案原始 BEC 最大差异 0.00104 e，内部振动频率最大差异
0.0184 cm^-1；全部模式最大差异 0.769 cm^-1 来自近零刚体轴向转动，已分别
通过本征矢识别。原始 Hessian 相对差异 4.91e-5。原始证据与计时账本保存在
`Nanowire_Sb2S3/results/benchmark/`。

BN(9,0) 对应的差异为 0.000208 e、0.514 cm^-1（约 48 cm^-1 的最低内部模式对）
和 1.18e-5，其全部内部模式仍为正频率。证据采用相同目录结构。BN9 的 BEC
位移仅由 60 减至 56，因为真空超胞可用对称性只是完整杆群的子群；主要节省来自
避免额外重复的 56 次力计算，不声称当前位移数量已达到完整杆群下的理论最小值。

在仓库根目录可重新导出数据和对照图：

```bash
python tools/shared_response/export_one_dimensional_bec.py
python tools/shared_response/plot_sb2s3_comparison.py examples/IR_Raman_Spectra/Nanowire_Sb2S3 --packaged --with-structure
python -m tools.shared_response.verify_one_dimensional_example --case examples/IR_Raman_Spectra/Nanowire_Sb2S3 --verify-archive
python -m tools.shared_response.verify_one_dimensional_example --case examples/IR_Raman_Spectra/Nanotube_BN_9_0 --verify-archive
```

最后两条命令无需 DFT/PYATB 可执行文件，仅使用仓库的 Python 依赖，即可只读重建
张量、重算两种谱线并核查原始证据哈希。有完整 benchmark 时还核查计时账本。
该检查不修改案例文件，也不等同于相对实验的电子响应近似精度验证。

## 周期设置

ZStar 使用 `dim=1` 表示仅沿一个晶格方向周期的体系。当前正式的
ABACUS + PYATB 工作流要求周期方向为笛卡尔 `z`，两个非周期晶格矢量分别与
`x`、`y` 对齐，因此真空只位于横向截面。

## 物理约定

一维体系需要混合极化处理。周期 `z` 分量采用 PYATB 的 Berry 相位极化；局域的
横向 `x/y` 分量由中性 ABACUS 电荷密度 cube 的实空间偶极积分获得。对于沿
`beta` 方向的原子位移，ZStar 按统一数据约定组装

```text
Z*(beta,alpha) = d p_alpha / d u_beta
```

即行表示原子位移/力，列表示极化/电场。横向两列来自实空间偶极，周期方向一列
来自 Berry 极化导数。最终 BEC 的单位为 `e`，与横向真空大小无关。

当前 PYATB 即使收到 1D 周期掩码，也会固定计算三个方向的 Berry 回路。因此
ZStar 会把生成的极化网格由 `1 x 1 x N` 自动补为可运行的最小
`2 x 2 x N`，并在 `zstar_pyatb_polarization_compat.json` 中记录该调整；最终只
采用物理周期方向 `z` 的结果。这只是对上游程序的兼容处理，不代表用 Berry 相位
描述横向极化。

横向有限差分还要求高精度电荷密度 cube。ZStar 会为低维极化/BEC 阶段写入
`out_chg 1 10`；第二个参数可避免默认的低精度舍入误差淹没微小偶极差。
开放方向采用离子价电荷加权的周期圆均值作为展开中心，因此即使纳米线跨越超胞
边界，也会作为连续整体积分，而不会被超胞切面分割。

超胞介电张量本身依赖真空。ZStar 因此在 `response.json` 中给出本征电子
线极化率

```text
alpha_1D = A_perp (epsilon_supercell - I) / (4 pi)
```

单位为 `Angstrom^2`。光谱与 `zstar dielectric static` 的频率响应在结果文件中明确写为
`alpha_1D/epsilon_0 = A_perp (epsilon_supercell - I)`，单位同为 `Angstrom^2`。

## Unified BEC 与 Gamma 声子工作流

在新的工作目录中生成默认的 Phonopy 对称性约化位移。将 `KPT` 放在指定的
`INPUT` 同级目录，保留案例的轴向 k 网格：

```bash
zstar bec pre --stru STRU --input INPUT --dim 1 --symmprec 1e-5

zstar bec job --system shell --dim 1 --output run.sh
bash run.sh

zstar bec stat --root .
zstar bec post --root .
```

默认 `--ensemble phonopy`、`--method auto` 从同一套 SCF 的极化与力重建 BEC
和 Gamma Hessian，Gamma 谱学无需再单独生成声子力计算。显式指定
`--ensemble cartesian` 才进入保留的旧笛卡尔 BEC 路线，不应与默认统一框架混淆。
执行器首先计算 `0.no-move`，然后用 PYATB 检查沿周期方向自动生成的一维高对称
能带路径。若带隙低于阈值，全部位移计算开始前即停止。每个位移复用参考态电荷
密度，重启时自动跳过已经完成的阶段。

主要输出包括：

- `BEC.dat`：经对称展开和电中性修正的全原子 BEC；
- `BORN`：超胞电子介电张量与原胞 BEC；
- `response.json`：包含本征线极化率的计算器无关响应记录；
- `FORCE_CONSTANTS`、`qpoints.yaml`：Gamma 力常数与本征模；
- `response_fit.json`：真实位移、同一计算的极化与力观测、拟合诊断；
- `BEC.raw.dat`、`FORCE_CONSTANTS.raw`：约束投影前的原始结果。

软件可执行文件与 MPI/OMP 设置可来自 ZStar 配置。队列、资源头和 module 激活
放在 header 中，优先级为 **Specified**（`--header FILE`）> **Current**
（`./header.sh`）> **Global**（`~/.zstar/header.sh`）。没有 header 时生成带简短
注释的可编辑模板。

## Gamma 点声子、IR 与 Raman

BN 与 Sb2S3 案例直接使用 unified 输出的 `qpoints.yaml`；配套 `run.sh` 完成
刚体模检查及完整 IR/Raman 流程。仅在需要有限波矢声子时另建轴向超胞：

```bash
zstar phonon pre --stru STRU --dim "1 1 2" --physical-dim 1
# 运行所有 disp-* ABACUS 力计算。
zstar phonon run --root .
zstar phonon post --root .
zstar phonon irrep --root . --file irreps.yaml --mode db --acoustic-thz 0.5
```

该 Gamma 点流程不要添加 `--nac`。三维 bulk 的非解析修正不能代替一维长程静电。

自由纳米线在 Gamma 点有四条声学分支：一条纵向、一条扭转和两条弯曲分支。弯曲
模对有限位移和力常数噪声尤其敏感，因此可能表现为很小的虚频。上面的显式
`0.5 THz` 分类阈值适用于随软件分发的 GaAs 基准，其中下一个光学模约为
`1.29 THz`，两者分离清楚；用户应针对自己的结构检查这一分离，不能机械套用。

计算 Gamma 点 IR 响应：

```bash
zstar ir --qpoints qpoints.yaml --born BEC.dat \
  --dielectric BORN --dim 1 --periodic-axis z --outdir ir_spectrum

zstar dielectric static --qpoints qpoints.yaml --born BEC.dat \
  --dielectric BORN --dim 1 --periodic-axis z --outdir dielectric_response
```

Raman 计算先从 `qpoints.yaml` 中选择稳定的光学模式：

```bash
zstar raman prepare --stru STRU --qpoints qpoints.yaml \
  --modes 17,21,24,29,37,39,40,41,55,57 --outdir raman
zstar raman run --raman-dir raman --reference 0.no-move \
  --qpoints qpoints.yaml --dim 1 --periodic-axis z \
  --abacus-command "mpirun -np 20 abacus" \
  --pyatb-command "mpirun -np 20 pyatb"
```

ZStar 在计算 Raman 活性前，会把依赖真空的介电导数转换为线极化率导数
`d alpha_1D / dQ`，单位为 `Angstrom^2/(Angstrom sqrt(amu))`。
上述模式列表复现 GaAs 验证中的代表性子集，并覆盖 `mm2` 点群的四类不可约表示。
它属于选模 Raman 基准；配套的 IR 计算则使用 BEC 与全部稳定光学模进行收缩。

## 旧 GaAs 基准（BEC 与声子分开计算）

随软件分发的 24 原子氢钝化 GaAs 纳米线完成了 49 个参考/BEC 阶段和 40 个声子
力计算阶段，默认 PYATB 路径带隙为 `3.3994 eV`。与独立 VASP 计算自动匹配
原子后，全张量 BEC 的 RMS 差为 `0.02068 e`，最大分量差为 `0.08906 e`。
周期方向线极化率在 ABACUS + PYATB 和 VASP 中分别为 `27.099 Angstrom^2` 与
`27.218 Angstrom^2`。

四条近零 Gamma 分支位于 `-10.00` 至 `-1.70 cm^-1`。对于 `800 cm^-1` 以下
的 56 个稳定晶格模，与归档 Quantum ESPRESSO 参考相比，`MAE = 7.6878 cm^-1`，
`RMSE = 8.8459 cm^-1`。ZStar 保留了全部 68 个正频 IR 模式，并通过 20 个正负
电子响应阶段完成公开说明的 10 模式 Raman 子集。紧凑输入、输出、哈希和绘图
源数据归档于 `docs/paper_figures/source_data/gaas_nanowire`。

同口径 VASP 比较只采用周期 `z` 方向的电子线极化率。VASP `LEPSILON` 包含
DFT 局域场效应，而 PYATB Kubo 响应属于独立粒子近似，因此横向电子响应差异
保留为方法约定诊断，不表述为数值一致。

## 无需氢钝化的新增案例

`examples/IR_Raman_Spectra` 新增 `Nanotube_BN_6_0`、`Nanotube_BN_9_0`
和 `Nanowire_Sb2S3`。两个 BN 管采用 PBE，Sb2S3 孤立完整链采用 PBE-D3(BJ)，
没有启用 HSE。三个结构均在 xy 横截面居中、沿 z 周期，不添加氢。
每例包含 `run/`、原始优化输入 `run/relaxation/`、`results/`、中英文 README、
`run.sh`、赝势、轨道，以及可用 VESTA 打开的优化后 `structure.vasp`。

| 体系 | band gap (eV) | 非刚体 Gamma 模数 | 最低频率 (cm^-1) | BEC + Gamma 核时 | Raman 核时 |
|---|---:|---:|---:|---:|---:|
| BN(6,0) | 2.799 | 68 | 99.20 | 27.0 | 119.8 |
| BN(9,0) | 3.813 | 104 | 47.92 | 125.0 | 294.3 |
| Sb2S3 | 1.501 | 26 | 39.38 | 18.9 | 30.1 |

表中为已完成 ABACUS + PYATB 调用的分配核时，不含准备开销和结构优化，
也不含 BN(9,0) 在 cu20 重启时无法追回的 PYATB 中断机时。三套结构优化分别为
13.6、22.4、36.1 核时。完整分项见各例 `results/compute_costs.json`，
不要把分配核时理解为按实际 CPU 利用率积分的时间。

执行器保护输入与已有结果目录，检查输入哈希，复用完成阶段，并检查参考结构
的绝缘性与残余力。三个位移刚体模和一个轴向转动模通过质量加权本征向量识别；
其余模式全部计算，不为使曲线吻合而调整峰位或强度。

BN(6,0) 七个候选 IR 分支与 Erba 等的 CRYSTAL/B3LYP 表 I
（[DOI](https://doi.org/10.1063/1.4788831)）相比，频率差异不超过约 3.1%；
径向呼吸模为 408.45 对 414.41 cm^-1，径向投影为 0.99684。候选对应基于
各频段内的顺序、简并性及偏振，不能称为与参考本征向量的逐一匹配。
BN(9,0) 与 Wirtz 等的 Raman 结果
（[DOI](https://doi.org/10.1103/PhysRevB.71.241402)）开展定性对照，
低频相对强度存在明显差异；文献的横向去极化/局域场处理不能直接等同于
PYATB 的独立粒子响应。

Sb2S3 的对照图直接使用公开
[CRYSTAL/B3LYP-D3(BJ) 数据集](https://doi.org/10.17632/6tntvw37tr.1)
提供的原始 IR/Raman 曲线，不移峰。Raman 相对强度明显不同，不宣称定量吻合。
参考中 31.5762 cm^-1 模式的轴向刚体转动投影约为 98.3%，依据原文打印的
本征向量估计；该峰仍保留在原始参考曲线中并予以说明。

## 按维度组织的 BEC 案例

按维度组织的 BEC/声子案例位于 `examples/1D_Nanowire/BN_9_0` 与
`examples/1D_Nanowire/Sb2S3`，均含 `run/`、`results/` 和 `run.sh`。
以下命令只核验响应张量、Gamma 模式和原始档案，不宣称核验了光谱：

```bash
python -m tools.shared_response.verify_one_dimensional_example \
  --case examples/1D_Nanowire/BN_9_0 --verify-archive --response-only
```

完整谱学档案仍在 `IR_Raman_Spectra/`。不加 `--response-only` 时，验证器仍然
要求完整 IR/Raman 文件，不会自动跳过缺失的光谱。

## 有限波矢边界

Gamma 点的模式分辨 IR 和 Raman 谱已经有严格定义并得到支持。对于有限波矢，极性
一维声子的长程静电核不同于 bulk 和 slab。ZStar 会拒绝对 `dim=1` 使用 bulk/Gonze
NAC；包含极性长程项的声子色散仍要求计算器提供真正的 1D Coulomb cutoff。参见
[Rivano、Marzari 与 Sohier（2023）](https://doi.org/10.1038/s41524-023-01140-2)
和 [Rivano、Marzari 与 Sohier（2024）](https://doi.org/10.1103/PhysRevB.109.245426)。
