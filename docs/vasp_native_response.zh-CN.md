# VASP 原生响应工作流

ZStar 优先使用 VASP 原生求解器，不将 ABACUS+PYATB 的有限位移重建算法
强加给 VASP。原生响应扩展已完成 SiC 和 AlN 的实机验收，目前保留在独立
开发分支，尚未合并主发布版。复现时请安装此 checkout：`pip install '.[vasp]'`。

## 准备与运行

在 `input/` 中准备 `INCAR`、`POSCAR`、
`KPOINTS` 和具有许可的 `POTCAR`：

```bash
zstar bec pre --calculator vasp --input-dir input --root response --phonons
zstar bec job --root response --system slurm --header header.sh --tasks 32 \
  --vasp-command 'mpirun -np 32 vasp_std'
sbatch response/run_vasp_bec.slurm
zstar bec post --root response
```

工作流先完成参考 SCF 并检查带隙，再进行原生响应计算。LDA/GGA 的
`--phonons` 采用 `LEPSILON=.TRUE.`、`IBRION=8`，输出 BEC、电子介电、
Γ 点模式以及相应离子响应。`BORN` 按 Phonopy 格式输出；`BEC.raw.dat`
保存完整原子张量。`qpoints.yaml` 与 `FORCE_CONSTANTS` 可被现有后处理复用。
同时导出 `phonopy.yaml` 和 `irreps.yaml`，供现有声子与模式分类入口使用。
原胞 Γ 点力常数不等于完整声子色散；声子能带仍需要足够大的超胞。
原生离子响应保持 VASP 对称性开启：源输入已有 `ISYM = 1/2/3` 时予以保留，
未设置或写成 `0/-1` 时改为 PAW 默认的 `ISYM = 2`。参考和响应阶段同时采用
`NCORE = 1` 并移除 `NPAR`，从而规避已经在 VASP 6.3.2 观察到的
`NCORE > 1` 对称 k 点重分配冲突，而不是关闭 `IBRION = 6/8` 所依赖的
对称约化。纯电子 `LEPSILON`/`LCALCEPS` 计算保留源输入或 VASP 默认的
对称性与并行策略；所有覆盖均写入 manifest。MPI 进程数仍由 Slurm 分配和
运行命令决定，不能把 `NCORE` 误当成 MPI 进程数。

spglib/Phonopy 的结构识别阈值与 VASP 的无量纲 `SYMPREC` 是两个不同参数。
ZStar 不会把结构侧的 `symprec=1e-3 A` 直接写入 VASP。原生离子响应中，未设置
`SYMPREC` 时保留 VASP 默认值，用户明确给出的更紧阈值也保持不变；若继承值宽于
`1e-4`，则收紧到 `1e-4` 并写入 manifest。GaN 和 ZnO 的精确
`eta_4=-0.005` 输入已经复现：`SYMPREC=1e-3` 会导致直接/倒易 Bravais 类型不一致，
而同一输入在 `1e-4` 下可正常进入 SCF。

`vasp_native_response.json` 分别保存电子/声子/总介电响应、钳制/离子/总压电
贡献和适用的弹性及 d 张量。低维结果明确标记为周期超胞响应，不直接称为本征
Bulk 常数。二维谱学的现有保护仍保留，待边界条件与转换完成验证后再开放。

## 具有压电响应的 AlN 案例

[纤锌矿 AlN 案例](../examples/VASP_Native_Response/AlN/README.zh-CN.md)
从结构优化开始，对比原生 DFPT 和原生应变有限差分，再计算 IR 及模式差分 Raman 谱。
验收包含独立压电分量 `e31`、`e33`、`e15`、介电闭合与 `e = d C`。
内部应变平移平衡不通过时保留原始张量并给出警告，不静默投影；只要总 e 与
relaxed-ion C 通过各自的一致性检查，仍按 `d=eC^-1` 输出并记录闭合残差。
保留的 PBE PAW 响应与谱学选择定则验收均通过：
e31=-0.582、e33=1.462 C/m²，原生应变路线 d33=5.324 pm/V。
[验收记录](development/vasp_native_AlN_validation_20260918.md) 保存计算来源与当前状态。

## 复用与 Raman

IR 与声子频率介电响应直接复用 BEC 和模式，不需重新运行位移 SCF。
已完成的原生工作流还可作为谱学参考阶段：

```bash
zstar spectra pre --calculator vasp --response response --kind ir --root ir
zstar spectra run --root ir
zstar spectra post --root ir
zstar spectra pre --calculator vasp --response response --root raman
zstar spectra job --root raman --system slurm --header header.sh --tasks 32 \
  --command 'mpirun -np 64 vasp_std'
sbatch raman/run_zstar_spectra.slurm
zstar spectra post --root raman
```

`--kind ir` 不生成 Raman 位移任务；参考响应完整时无需额外 VASP 调用。
导出模式编号按频率升序排列，`spectra_results.json` 中的
`native_mode_numbers` 保留 VASP XML 源编号。后续复用 Raman 张量时应使用
JSON 及其匹配的 `qpoints.yaml`，而不是缺少编号的张量子集 `.npy`。
旧版原生 JSON 若缺少编号约定，只需重做 `zstar spectra post`，不必重算 DFT。
Raman 需要介电/极化率对振动坐标的导数，因此仍采用正负模式位移上的原生
介电响应。它不能被表述为一次 DFPT 自动产生完整 Raman 张量。使用
`--response` 时，输入及参考响应来自同一原生工作流，并以普通文件复制方式
复用参考输出和重启文件，不使用软链接。

## 方法选择与弹性

### 只求 e 与同时求 d

只求包含离子弛豫的压电应力系数 `e`，可直接请求原生响应：

```bash
zstar bec pre --calculator vasp --input-dir input --root piezo --piezo
zstar bec run --root piezo
zstar bec post --root piezo
```

`--piezo` 自动包含 Γ 点力常数，无需再加 `--phonons`。LDA/GGA 采用原生
`LEPSILON + IBRION=8`，收集电子、离子及总压电贡献。内部应变耦合本身不是
压电张量；VASP 将原子弛豫响应与 BEC 结合得到离子贡献，ZStar 直接读取，
不另建外部应变/极化差分任务来重复计算。

| 所需结果 | 准备选项 | 原生求解与复用 |
| --- | --- | --- |
| BEC、电子介电 | 无额外选项 | LDA/GGA 电场 DFPT |
| 含离子弛豫的压电 e | `--piezo` | 电场 DFPT 与原生 Γ 点离子响应 |
| Γ 点声子、声子介电、IR | `--phonons` | 同一原生离子响应；IR 只做后处理 |
| 完整弹性 C 与推导的 d | `--elastic` | 原生离子/应变有限差分；`d = e C^-1` |
| Raman | 后续 `zstar spectra pre --response ...` | 额外模式位移上的原生介电响应 |

需要 `d` 时改用 `--elastic`，该选项已包含必要的离子响应。仅 `--piezo` 或
`--phonons` 不提供完整弹性矩阵。应变有限差分由 VASP 内部执行，不是 ZStar
生成的另一套外部应变计算。AlN/SiC 案例同时比较两条原生路线是验证安排，
不是日常计算 `e` 的必需步骤；Raman 也不是一次电场/声子 DFPT 自动给出的。
方法边界见 [LEPSILON](https://vasp.at/wiki/LEPSILON)、
[声子 DFPT](https://vasp.at/wiki/Phonons_from_density-functional-perturbation_theory)和
[原生有限差分](https://vasp.at/wiki/Phonons_from_finite_differences)官方说明。

默认 `--method auto` 优先采用原生电场 DFPT；杂化或 meta-GGA 泛函选择
原生有限电场。显式指定不兼容的 `--method dfpt` 会报错并提供指引。
有限电场路线的 Γ 点声子采用原生有限差分。方法选择并不等于任意泛函均已
经过实机验证；仍需针对泛函与体系验证。

`--elastic` 仅用于三维 Bulk，采用 `IBRION=6, ISIF=3` 的原生离子/应变
有限差分；LDA/GGA 电场响应仍采用 DFPT。输出将 kbar 转为 GPa，将 VASP
的列顺序转换为 `(xx, yy, zz, yz, xz, xy)`，应变采用工程剪切约定。
机械稳定且满足主对称性时才输出 d。原生压电张量不再重复应用针对 improper
极化差分的几何修正。电子和离子压电贡献须同时存在；若 VASP 显式打印总压电
张量，其与两项之和的差异须不超过 1e-4 C/m²。ZStar 同时记录 C 的条件数以及
`e = d C` 的闭合残差。内部应变平移平衡是离子贡献分解的独立诊断：未通过时
保留警告和原始数据，但在总 e 与 relaxed-ion C 各自通过检查时，不应错误阻断
代数关系 `d = e C^-1`。上述条件属于一致性检查，不能代替截断能、k 点及响应的
收敛验证。
原生 JSON 与通用响应记录保存求解来源，区分原生 DFT、代数转换得到的 d 和
IR 后处理。检查失败时保留原始张量与原因，不静默切换算法或自动重跑。

## 作业头部

```bash
#!/usr/bin/env bash
#SBATCH --partition=hfacnormal01
#SBATCH --nodes=1
#SBATCH --ntasks=32
#SBATCH --cpus-per-task=1
#SBATCH --time=02:00:00
source /public/home/iai806/Software/VASP/env.sh 6.3.2
```

不指定节点、不使用 `--exclusive`。header 优先级是 Specified、Current
(`./header.sh`)、Global (`~/.zstar/header.sh`)。VASP 赝势不公开分发；
用户按 POSCAR 元素顺序，从 `$VASP_PSEUDO_ROOT/PBE/元素/POTCAR` 组装。

理论依据与方法适用范围见[英文指南](vasp_native_response.md)。

[3C-SiC 案例](../examples/VASP_Native_Response/3C_SiC/README.md) 已包含实际计算的
原生响应及 IR/Raman 谱。故意将 IR 缓存复用的启动命令设为 `false` 后流程
仍成功，确认没有额外 VASP 调用。光学 Raman 三重简并模的活性相差低于
0.02%，退偏比接近 0.75；这些属于内部一致性验证，不代表任意泛函均已验证。
