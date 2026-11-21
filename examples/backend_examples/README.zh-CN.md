# 计算器后端案例

这些案例展示计算器无关的 ZStar 分析如何连接 CP2K、Quantum ESPRESSO 和 VASP。各后端使用各自的输入格式和响应约定。

## CP2K

- `cp2k_bec/H2O`：ZStar 中心差分 BEC 与 CP2K 原生 APT 的定量逐分量对比。
- `cp2k_bec/MgO`：周期体系 BEC 与原生 `APT_FD` 的诊断，并保留声学和残差。
- `calculator_spectroscopy/cp2k_h2o`：CP2K H2O IR/Raman 可运行案例及参考谱图。

具体命令见 `cp2k_bec/H2O/README.md`。运行需要用户自行提供 CP2K 可执行
程序和 CP2K 数据目录，仓库不捆绑它们。

## Quantum ESPRESSO

- [CO₂ 和 SiC 算例](qe_bec/)提供两次 QE 6.2.1 实际运行的输入、原始输出和 ZStar 响应数据。两个算例都跑完了 `pw.x`、`ph.x` 和 `dynmat.x`。

## VASP

`calculator_spectroscopy/vasp_sic/` 说明所需的 `INCAR`、`POSCAR`、`KPOINTS`、
授权的 `POTCAR` 和 `vasprun.xml`。`calculator_spectroscopy/vasp_sic/results/` 保存
精简响应数据和谱图。`POTCAR` 必须由用户在授权范围内取得，不得提交。

运行后端流程前，可用 `zstar backend list --check` 和 `zstar config check`
检查可执行程序解析结果。

各算例在 `run/` 存放输入，在 `results/` 保存结果。提供 `run.sh` 的 CP2K 和
VASP 算例可用 `bash run.sh --dry-run` 查看运行顺序。
