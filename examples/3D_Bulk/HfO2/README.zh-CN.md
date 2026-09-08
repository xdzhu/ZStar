# 四方 HfO2：BEC 与介电响应

当前验证输入采用 PBEsol、ONCV 赝势、Hf 6s3p3d2f1g 和 O 2s2p1d
的 **9-bohr** 轨道、100 Ry、Gamma 中心 10x10x7 网格、SCF 阈值 1e-8。
六原子 P42/nmc 晶胞的 a=3.55652、c=5.13487 Angstrom。

`run/` 是含赝势和轨道的干净输入；`results/` 是已验证的 BEC、
声子、谱学和介电曲线，设置见 `provenance.json`。旧 10-au 输入及
旧张量保存在 `legacy/before_20260906/`，不要与当前结果混用。

```bash
bash run.sh --dry-run
ABACUS_COMMAND="mpirun -np 40 abacus" PYATB_COMMAND="pyatb" bash run.sh --stage all
```

先安装当前 ZStar 与 PYATB 并加载集群环境。新计算写入 `work/`，
不覆盖 `results/`。默认 unified 流程为 1 个参考 SCF 加 4 个约化
位移，导数采用实际写入结构的位移矢量。完成后在 `work/` 中运行：

```bash
zstar dielectric static
zstar dielectric freq --plot
```

文献对照张量原用中心差分 0.01 Angstrom，默认 unified 位移为
0.02 bohr；允许存在有限步长差异。同设置的精度与计时档案见
`3D_Bulk/t_HfO2/`。Raman 还需要极化率导数，完整流程见
`IR_Raman_Spectra/Bulk_HfO2/`；这里不声称验证全波矢稳定性或 LO-TO 劈裂。
