# BN(9,0) nanotube

采用 ABACUS + PYATB，PBE 泛函，`dim=1`，z 方向周期；不需要氢钝化。
结构主体已平移到 xy 横截面中心。`structure.vasp` 用于 VESTA 等结构查看工具，
不表示此案例使用 VASP 计算。

## 快速复算

也可先在仓库根目录只读核查已有结果，无需 ABACUS/PYATB：

```bash
python -m tools.shared_response.verify_one_dimensional_example --case examples/IR_Raman_Spectra/Nanotube_BN_9_0 --verify-archive
```

该命令重建 BEC/力常数、重算 IR/Raman 并核查归档哈希，不修改案例文件。
它确认计算档案可复现，不替代与实验的物理精度对照。

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

`results/BEC_comparison/` 保存完整笛卡尔张量及逐原子径向/切向/轴向变换后的
元素平均和范围。B 的三个对角均值为 `(0.397, 1.256, 2.745) e`，N 为
`(-0.474, -1.178, -2.745) e`。电中性在共同笛卡尔系中核验，不能直接对不同
原子的局域基底分量求和。

本案例确实使用 unified：56 个位移加 1 个参考 SCF，同步得到 BEC 与 Gamma
力常数，ABACUS+PYATB 合计 125.04 核时。独立旧方案需要 61 个 BEC SCF 与
56 个声子力 SCF，共 117 次；对应 140.05、130.36 核时，合计 270.41 核时。
实测加速 2.16 倍、节省 53.8%，而非用 SCF 数量比估算。旧方案的第
43 个声子力任务中断，完整耗时未记录；保留前 42 个成功结果后，在新任务中完成了
剩余 14 个。上述核时仅统计成功计算，不能当作包含中断损耗的总计费量。
`results/benchmark/` 保存中断现场、成功日志、输入、计时账本与哈希。
更早的 Raman 重启记录另归谱学成本，不计入这里的 BEC+声子对照。

新旧原始 BEC 最大差异 0.000208 e，原始 Hessian 相对差异 1.18e-5；内部模式
最大频率差异为 0.514 cm^-1，出现在约 48 cm^-1 的最低频模式对。104 个内部
模式均为正频率，两套方案分别通过本征矢识别四个刚体模式。

`BEC.dat` 与 `response.json` 都是位移在前、极化在后；重建文件
`response_fit.json` 以及这里导出的展示 CSV 是极化在前、位移在后。
使用非对角分量前必须确认约定。

### 谱学边界

band gap 为 3.813 eV；有 104 个正频率非刚体 Gamma 模式，最低
47.92 cm^-1。这不是全布里渊区稳定性验证。
三个位移刚体模和一个轴向刚体转动模按本征向量识别，不任意删峰或平移峰位。
一维响应报告线极化率，不把含真空的超胞介电常数称为纳米线本征介电常数。

不同泛函、电子响应近似和横向去极化处理会影响文献比较；频率接近不等于
Raman 绝对强度已验证。Sb2S3 的 Raman 相对强度与 B3LYP-D3(BJ) 参考明显不同，
不能宣称定量吻合。BN(9,0) 曾有一次任务中断，计时表不包含无法追回的中断损耗。
详细参数、单位、文献 DOI 和比较限制见英文 README 与结果元数据。
