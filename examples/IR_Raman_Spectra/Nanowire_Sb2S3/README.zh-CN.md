# Sb2S3 isolated full chain

采用 ABACUS + PYATB，PBE-D3(BJ) 泛函，`dim=1`，z 方向周期；不需要氢钝化。
结构主体已平移到 xy 横截面中心。`structure.vasp` 用于 VESTA 等结构查看工具，
不表示此案例使用 VASP 计算。

## 快速复算

保留完整 ZStar 仓库，激活包含依赖与 PYATB 的 Python 环境，并配置 ABACUS。

```bash
bash run.sh --dry-run
export OMP_NUM_THREADS=1
export ABACUS_COMMAND="mpirun -np 40 abacus"
export PYATB_COMMAND="mpirun -np 40 pyatb"
bash run.sh
```

软件路径、MPI 命令按本地环境替换。脚本使用上述环境变量或同名命令行参数；
队列头与 module 放在外层作业脚本中。原始生产任务采用 ABACUS 1 MPI x 40 OMP、
PYATB 40 MPI x 1 OMP，因此示范启动配置不是严格机时 benchmark 的相同并行配置。

`run/` 仅保存优化后的输入、赝势与轨道；`run/relaxation/` 保留原始结构优化输入。
`results/` 保存已有结果、诊断和带哈希的原始证据包；新计算输出到 `work/`。
默认从优化好的结构开始，避免无意覆盖输入和参考结果。需要重新优化时，将
`run/relaxation/` 复制到新工作目录再运行 ABACUS，检查几何收敛、力和轴向应力，
并将优化后的结构重新居中。再次运行脚本会复用已完成阶段。

可使用 `--stage response` 仅计算 BEC 和 Gamma 声子，`--stage raman` 继续谱学，
`--stage post` 重做已有 Raman 后处理，或用 `--work` 指定新目录。

## BEC 展示与统一计算成本

`results/BEC_comparison/` 保存完整张量、五类代表位点的三组对角分量及参考
原子的坐标匹配记录。代表原子 `(7,8,1,2,3)` 的轴向 BEC 为
`(4.642,5.972,-4.101,-3.353,-3.159) e`；参考为
`(4.341,6.135,-3.786,-3.430,-3.260) e`。参考来自 Ulian 的公开计算数据集
（DOI: 10.17632/6tntvw37tr.1），尚未核实对应期刊论文。PBE-D3(BJ) 与
B3LYP-D3(BJ) 使用分别优化的同类孤立链，不能称为同方法精度验证。

本案例确实使用 unified：20 个位移加 1 个参考 SCF，同时得到 BEC 与 Gamma
力常数，合计 18.95 核时。旧方案需要 31 个 BEC SCF 与 20 个独立声子 SCF，
共 51 次，分别耗费 23.74、17.93 核时，合计 41.67 核时。实测加速 2.20 倍，
节省 54.5%。`results/benchmark/` 保存对照输入、原始 SCF 日志、计时账本和哈希。
两套方案原始 BEC 最大差异为 0.00104 e，内部振动频率最大差异为 0.0184 cm^-1，
原始 Hessian 相对差异为 4.91e-5。全部模式的最大差异 0.769 cm^-1 来自近零的
刚体轴向转动，两套方案均通过本征矢独立识别。额外 52 个 Raman 位移不计入
BEC+声子 benchmark。

在仓库根目录执行以下命令，无需 ABACUS/PYATB，即可只读重建张量、重算谱线、
核查证据哈希和机时账本，不修改案例文件：

```bash
python -m tools.shared_response.verify_one_dimensional_example --case examples/IR_Raman_Spectra/Nanowire_Sb2S3 --verify-archive
```

该检查确认归档可复现，不等同于相对实验的物理精度验证。

`BEC.dat` 与 `response.json` 是位移在前、极化在后；`response_fit.json` 和
展示 CSV 为极化在前、位移在后。仓库根目录运行以下命令可重绘结构/IR/Raman图：

```bash
python tools/shared_response/plot_sb2s3_comparison.py examples/IR_Raman_Spectra/Nanowire_Sb2S3 --packaged --with-structure
```

结构仅在绘图时重复三个轴向周期，未扩胞重算。灰线保留原始参考样本及其
低频转动样特征；独立图中的参考编号仅用于此图。

### 谱学边界

band gap 为 1.501 eV；有 26 个正频率非刚体 Gamma 模式，最低
39.38 cm^-1。这不是全布里渊区稳定性验证。
三个位移刚体模和一个轴向刚体转动模按本征向量识别，不任意删峰或平移峰位。
一维响应报告线极化率，不把含真空的超胞介电常数称为纳米线本征介电常数。

不同泛函、电子响应近似和横向去极化处理会影响文献比较；频率接近不等于
Raman 绝对强度已验证。Sb2S3 的 Raman 相对强度与 B3LYP-D3(BJ) 参考明显不同，
不能宣称定量吻合。BN(9,0) 曾有一次任务中断，计时表不包含无法追回的中断损耗。
详细参数、单位、文献 DOI 和比较限制见英文 README 与结果元数据。
