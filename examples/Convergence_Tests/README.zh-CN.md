# 收敛性测试

这里将数值收敛性检查与正文科学案例分开保存，并复用生产案例的公开输入和
Unified BEC/Gamma 工作流。

- `SiC_Displacement/`：扫描 0.005--0.030 Angstrom 的六个位移幅度；
- `hBN_Vacuum/`：扫描单层 hBN 的 15、20、30 和 40 Angstrom 胞高，层始终
  位于真空中心。

每个目录均提供干净的 `run.sh`、分析脚本和保存精简表格及图片的 `results/`。
求解器输出写入独立的 `work/`，分析过程不会覆盖原始计算。Torque/PBS 集群可
用 `run_pbs.sh` 提交完整扫描；默认资源为 `gold5120` 队列、单节点 28 核，也可
通过 `ZSTAR_PBS_QUEUE` 和 `ZSTAR_PBS_PPN` 修改。
