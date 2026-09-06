# BN(6,0) nanotube

采用 ABACUS + PYATB，PBE 泛函，`dim=1`，z 方向周期；不需要氢钝化。
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

## 结果边界

band gap 为 2.799 eV；有 68 个正频率非刚体 Gamma 模式，最低
99.20 cm^-1。这不是全布里渊区稳定性验证。
三个位移刚体模和一个轴向刚体转动模按本征向量识别，不任意删峰或平移峰位。
一维响应报告线极化率，不把含真空的超胞介电常数称为纳米线本征介电常数。

不同泛函、电子响应近似和横向去极化处理会影响文献比较；频率接近不等于
Raman 绝对强度已验证。Sb2S3 的 Raman 相对强度与 B3LYP-D3(BJ) 参考明显不同，
不能宣称定量吻合。BN(9,0) 曾遇 cu20 重启，计时表不包含无法追回的中断损耗。
详细参数、单位、文献 DOI 和比较限制见英文 README 与结果元数据。
