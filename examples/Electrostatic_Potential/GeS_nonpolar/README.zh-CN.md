# GeS 高对称非极性静电势参考

本例与相邻 `GeS/` 极性案例配套。固定原晶胞，消除 Ge/S 沿扶手椅
方向的相对倾斜，并恢复同种原子的反演配对。原结构为 Pmn2_1，参考
结构为 Pmmn。这里只验证高对称非极性参考，并未证明其为过渡态。
**复现时直接固定离子做 SCF，不要先做无约束结构优化。**

构造依据为 [Fei、Kang 和 Yang (2016)](https://doi.org/10.1103/PhysRevLett.117.097601)
图 1(b) 的零倾斜参考；晶胞和原子来源仍为本项目的 GeS 档案。
`results/reference_construction.json` 记录坐标和原子映射。

```bash
bash run.sh --dry-run
bash run.sh
```

默认解压保留的 cube 到独立 `work/` 并重新生成平面图与方向曲线，
无需 DFT；不修改原始档案，不使用软链接。新工作目录必须不存在。
需要完整重算时，先通过 `zstar config` 设置 ABACUS 路径和 MPI/OMP，
加载集群运行环境，再运行：

```bash
bash run.sh --calculate --work work-new-scf
```

`run/` 仅包含输入、DOJO NC 赝势和 DZP 10-bohr 轨道；`results/` 包含
原始 SCF 日志、结构映射、压缩 cube、后处理数据与哈希证据。
设置与极性案例一致：PBE+D3(0)、100 Ry、kspacing 0.05 0.05 1、
scf_thr 1e-8、Gaussian 展宽 0.001 Ry。保留的 ABACUS 3.10.0 LTS
计算使用 40 核，39 秒完成并收敛。

3x3 扩胞仅用于绘图，中央单胞用虚线标出，不重新计算扩胞。
两张 GeS 平面图减去各自势均值后使用共同色标。沿 a 方向的镜像
不对称指标：非极性参考 2.36e-8，极性结构约 0.0983。
静电势图不是电荷密度图；该指标也不是极化大小。
