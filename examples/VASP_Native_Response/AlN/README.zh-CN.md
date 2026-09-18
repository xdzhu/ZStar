# 纤锌矿 AlN：VASP 原生响应全链路

四原子 PBE 案例从晶胞和内部坐标优化开始，依次计算 BEC、电子与声子介电张量、
Γ 点声子、压电及弹性张量、IR 与模式差分 Raman 谱。笛卡尔 z 沿 +c，轴向
Al 到 N 的键指向 +c。输入结构只是优化初始结构，不作为最终平衡结构。

## 运行

安装 ZStar 及 VASP 谱学依赖，加载 VASP 环境。设置 `VASP_PSEUDO_ROOT`；
脚本按 POSCAR 元素顺序读取授权赝势库中的 `PBE/Al/POTCAR` 和 `PBE/N/POTCAR`。

```bash
bash run.sh
```

合肥集群使用 `sbatch run_hf.slurm`，申请 64 MPI × 1 OMP，不排它、不固定节点。
使用 `NCORE = 4`，不写 NPAR。其他机器请修改 Slurm 头部及启动器。
测试版本采用 `ISYM = 0` 保持原生扰动中的 k 点集合不变，不宣称保留电子对称性约化。
可通过 `MPI_TASKS` 和 `VASP_COMMAND` 环境变量覆盖脚本的并行数与启动命令。

`run/` 是干净输入，`.work/` 是实际执行目录，`results/` 保存紧凑结果。
流程可续跑；优化未收敛或响应被拒绝会停止。改变参数时应新建执行目录，
不要混用旧的已完成阶段。POTCAR、WAVECAR、CHGCAR 不上传到仓库。

## 验收

同一优化结构对比原生 DFPT（IBRION=8）和原生应变有限差分
（IBRION=6、ISIF=3）；两者电子 BEC 和介电响应都采用 LEPSILON。
有限差分路线提供弹性常数；通过稳定性、矩阵对称性和内部应变平移平衡检查
后才输出 d 张量。Raman 是模式位移后的原生介电张量差分，不是 Raman DFPT。

`verify_results.py` 检查原始 OUTCAR 的 BEC、独立 XML 介电解析、电荷和规则、
光学模稳定性、静态介电闭合、6mm 压电张量形式、两条路线的频率一致性，
以及 `e = d C`。原生 DFPT 内部应变的警告原样记录，不静默投影修正。
这些是一致性检查，并不能替代数值收敛测试。

`verify_spectra.py` 检查平衡结构的 6mm 点群、九个光学模的编号与张量/频率
对应关系，以及 IR/Raman 选择定则。这里是未经方向性 NAC 修正的 Γ 点 TO 谱，
不代表方向分辨的 LO 分支或实验绝对强度。介电张量包含内部离子响应，但保持
宏观应变固定，不含自由应力下的宏观压电修正。

通过质量检查的原生应变路线得到 e31=-0.582、e33=1.462 C/m²，d33=5.324 pm/V。
历史优化与 DFPT 使用 EDIFF=1e-8，验收通过的弹性与 Raman 使用 1e-9；提供的
干净输入统一采用 1e-9。`results/stage_input_sha256.txt` 记录实际阶段输入的哈希。

优化完成后可以逐步执行：

```bash
zstar bec pre --calculator vasp --input-dir .work/input --root .work/elastic --elastic
zstar bec run --root .work/elastic --vasp-command 'mpirun -np 64 vasp_std'
zstar bec post --root .work/elastic
zstar spectra pre --calculator vasp --response .work/elastic --root .work/raman
zstar spectra run --root .work/raman --command 'mpirun -np 64 vasp_std'
zstar spectra post --root .work/raman
```

仅计算 IR 时增加 `--kind ir`，无需额外 VASP 作业。导出的 Raman JSON 与
`qpoints.yaml` 采用一致的频率升序编号，后续使用时应成对保留。

## 文献

优先对照 de Jong 等 2015 年的 VASP PBE PAW proper 压电结果：
e33=1.46 C/m²、e31=−0.58 C/m²，见论文 Technical Validation 小节。
[DOI:10.1038/sdata.2015.53](https://doi.org/10.1038/sdata.2015.53)，
[作者提供的全文](https://perssongroup.lbl.gov/papers/sdata2015-piezoprops.pdf)。
其截断能为 1000 eV，k 点密度约为每倒易原子 2000；本案例初始设置不完全相同，
偏差需要如实列出并按需检查收敛。

Bernardini 等 1997 年论文 Table II 的 LDA 超软赝势结果为：N 轴向 BEC
−2.70 e、e33=1.46 C/m²、e31=−0.60 C/m²。
[DOI](https://doi.org/10.1103/PhysRevB.56.R10024)，
[作者提供的全文](https://www.physics.rutgers.edu/~dhv/pubs/local_copy/fb_nit.pdf)。
与本案例 PBE PAW 设置不同，仅作背景参照；还需区分历史极化差分与 proper
压电定义。另见 Zoroddu 等对于 LDA/GGA 的研究：
[DOI:10.1103/PhysRevB.64.045208](https://doi.org/10.1103/PhysRevB.64.045208)。
