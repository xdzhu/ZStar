# ZStar v2：tetragonal BaTiO₃ 40×1 formal response run

日期：2026-09-12
分支：`zstar-v2-development`
状态：研究性算法/后处理验证，不是已发表的材料基准。

## 目的与边界

本轮只验证 v2 的应变响应数据链是否闭合：ABACUS SCF 输出力、应力和实空间矩阵，
随后对每个几何运行一次 v1 兼容的 PYATB 极化计算。PYATB 在一次运行中完成 a/b/c
三个 Berry loop；没有为三个方向分别启动 ABACUS NSCF。ABACUS `gdir=1,2,3` 仅作为
保留的可选交叉审计路径，本轮正式数据未使用。

结构是人为构造的非中心对称 `P4mm` tetragonal BaTiO₃ fixture。结果是固定离子、
直接有限差分的 raw `e`，尚未加入 proper/improper 修正、内部离子弛豫、应力符号独立
核查、机械稳定性、带隙/绝缘性收敛和独立后端比较，因此不能作为 BaTiO₃ 的发表值。

## 输入和软件

* ABACUS：`3.10.0-LTS`，commit `e84abb4`，可执行文件
  `/home/zhuxd/Software/abacus/INSTALL/3.10.0-LTS/bin/abacus`。
* PYATB：`/home/zhuxd/Software/anaconda3/envs/icu/bin/pyatb`；精度适配器是仓库中的
  `zstar/pyatb_precision.py`。该适配器不改变 PYATB 数值 kernel，保留默认六位小数
  文件，同时写出 16 位 `polarization.dat` 和 `zstar_precision.json`。
* 泛函/基组：PBEsol、ABACUS LCAO、`ecutwfc=100 Ry`、Gamma `9×9×9`、
  `scf_thr=1e-8`、`scf_nmax=200`；赝势为 `Ba.upf/Ti.upf/O.upf`（upf201），轨道为
  `Ba_gga_10au_100Ry_4s2p1d.orb`、`Ti_gga_10au_100Ry_4s2p2d1f.orb`、
  `O_gga_10au_100Ry_2s2p1d.orb`。
* ABACUS 官方输入文档将 `press1/press2/press3` 的正值定义为压缩外应力，输出规范
  将 stress 单位列为 kBar；这支持本报告的 compression-positive 候选，但仍不能替代
  对 `TOTAL-STRESS` 符号的受控独立核查（[ABACUS input parameters](https://abacus.deepmodeling.com/en/latest/advanced/input_files/input-main.html#press1)，
  [output specification](https://abacus.deepmodeling.com/en/v3.11.0-beta1/advanced/output_files/output-specification.html)）。
* 输入 fixture：`examples/3D_Bulk/tetragonal_BaTiO3/inputs/`。
  `INPUT` SHA256=`b1e34c2704a8ffb6e1a354bde00bccd16be8912eade23a096230f4f4813e89e5`；
  `STRU` SHA256=`9cec10dcce286cfa7f5401c8d5b2b34f151274ce3a63ebdcf4881c6142e207fb`；
  `KPT` SHA256=`36ed6ce38df591bb0c19c8c77ffed5527ff49d2e7eeaf3143785518b201a0085`。
  生成的 ensemble manifest SHA256=`0bdaa19e5ce1b80eb8fc4dd89a893cd2ed72ea7576acc610e3a27e1cb41696ff`。

## 任务和资源

采用三个位移/应变幅度 `|η|=5×10⁻⁴, 1×10⁻³, 2×10⁻³`，六个工程 Voigt 分量
`(xx, yy, zz, 2yz, 2xz, 2xy)` 的正负中心差分。任务图为 1 个 reference + 36 个
应变 stage，共 37 个结构。

每个任务均使用 `40 MPI × 1 OpenMP`，分配在 `cu24`、`cu25`、`cu26`，每节点 12 个
应变 stage；没有修改或抢占用户的 PBS 占位作业。

```bash
export OMP_NUM_THREADS=1
mpirun -np 40 /home/zhuxd/Software/abacus/INSTALL/3.10.0-LTS/bin/abacus
mpirun -np 40 python /home/zhuxd/zstar-v2-tbto-formal40-20260912/pyatb_precision.py
```

ABACUS：36 个应变 SCF 全部 `exit_code=0`，串行 wall-time 合计 4790 s，reference
115 s，含 reference 合计 4905 s。PYATB precision：36 个应变运行全部成功，合计
664 s，reference 218 s，含 reference 合计 882 s。每个几何只有一次 PYATB 运行，
其一次输出包含 a/b/c 三个方向。

## 结果和诊断

收集器：`backend=abacus+pyatb`，`stage_count=37`，`pyatb_run_count=37`，精度元数据
完整。空间群识别为 `P4mm`；输入设计矩阵秩 6，P4mm 允许子空间秩 3，约束拟合秩 3，
`complete=true`，条件数 `1.0000000000000413`，branch shift 最大值为 0。

精度输出的全幅度拟合最大残差为 `2.7884510811846536×10⁻⁶ C/m²`，RMS 为
`5.419210343094425×10⁻⁷ C/m²`，branch matching residual 最大值为
`8.926308651011903×10⁻⁴ C/m²`。逐幅度结果如下（raw `e`，单位 C/m²）：

| `|η|` | `e15=e24` | `e31=e32` | `e33` | 最大残差 (C/m²) |
|---:|---:|---:|---:|---:|
| 5e-4 | -0.0171210341 | -0.0545429115 | -0.4449132220 | 1.7355e-7 |
| 1e-3 | -0.0171341793 | -0.0545421688 | -0.4449150140 | 6.9994e-7 |
| 2e-3 | -0.0171320230 | -0.0545437452 | -0.4449232543 | 2.7844e-6 |

这些数值只证明“单次 PYATB 三方向极化 → branch matching → 非正交晶格方向投影
重建 → 对称约束拟合”的算法链；不构成已验证的压电系数。非正交晶胞的 Cartesian
重建解的是单位晶格方向投影方程，而不是把三个标量机械相加。

在同一 branch-matched reference 极化上，研究 API 还给出 Vanderbilt 几何修正后的
`e_proper`：`e31=e32≈0.29443253`、`e33≈-0.44492121`、
`e15=e24≈-0.19161988 C/m²`。这只是验证 raw→correction→proper 的矩阵变换，
因为本 fixture 尚未完成 proper finite-difference、离子弛豫和收敛/独立后端审计，
不能把这些数值当作最终 proper 材料常数。

同一批 ABACUS `stress_raw` 还做了一个显式假设为 compression-positive 的弹性拟合，
并开启 major symmetry 约束。候选矩阵的 `C11=374.4416`、`C12=129.6646`、
`C13=117.1720`、`C33=329.6101`、`C44=125.5997`、`C66=139.5320 GPa`，最大
拟合残差为 `0.06670 kbar`，对称化后的特征值均为正。这里的 sign 仍是待独立确认的
假设，且结构未做充分应变/截断/SCF 收敛，因此只作为弹性代码链和稳定性诊断候选，
不是正式 `C`。

## 输出和复现

原始远端目录为 `/home/zhuxd/zstar-v2-tbto-formal40-20260912`，本地归档在
`D:/Temp/zstar-v2-tbto-formal40-20260912`，其中保留 stage 输入、ABACUS/PYATB 日志、
precision 标记、collector JSON 和拟合诊断。仓库只提交小型摘要和 provenance，不提交
赝势、轨道、缓存或完整输出树。正式复现前应先运行单 stage smoke，再按节点并行恢复
未完成 stage。

下一道 Gate C 仍要求：应力单位/符号独立核对、能量曲率收敛、更多对称性和多材料案例、
relaxed-ion/internal-strain、独立后端或高精度参考，以及 proper/improper `e` 的明确定义。
