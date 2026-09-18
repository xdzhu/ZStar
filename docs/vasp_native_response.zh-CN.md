# VASP 原生响应工作流

ZStar 优先使用 VASP 原生求解器，不将 ABACUS+PYATB 的有限位移重建算法
强加给 VASP。原生响应扩展已完成 SiC 和 AlN 的实机验收。
复现时请安装包含这些扩展的源码：`pip install '.[vasp]'`；
较早发布的 wheel 可能尚不提供新增开关。

## 准备与运行

在 `input/` 中准备 `INCAR`、`POSCAR`、
`KPOINTS` 和具有许可的 `POTCAR`：

```bash
zstar bec pre --calculator vasp --input-dir input --root response --phonons
zstar bec job --root response --system slurm --header header.sh --tasks 64 \
  --vasp-command 'mpirun -np 64 vasp_std'
sbatch response/run_vasp_bec.slurm
zstar bec post --root response
```

工作流先完成参考 SCF 并检查带隙，再进行原生响应计算。LDA/GGA 的
`--phonons` 采用 `LEPSILON=.TRUE.`、`IBRION=8`，输出 BEC、电子介电、
Γ 点模式以及相应离子响应。`BORN` 按 Phonopy 格式输出；`BEC.raw.dat`
保存完整原子张量。`qpoints.yaml` 与 `FORCE_CONSTANTS` 可被现有后处理复用。
同时导出 `phonopy.yaml` 和 `irreps.yaml`，供现有声子与模式分类入口使用。
原胞 Γ 点力常数不等于完整声子色散；声子能带仍需要足够大的超胞。
参考 SCF、原生响应与 Raman 输入采用 `NCORE = 4`，移除 `NPAR`，
不同时设置这两个并行参数。HF 的 Slurm 分配内采用 `mpirun -np 64 vasp_std`。
采用 `ISYM = 0` 固定电子 k 点集合，以规避 VASP 6.3.2 在 `NCORE > 1`
时改变 k 点集合的限制。这会取消电子点群的 k 点约化，属于兼容性设置；
不能据此宣称原生声子扰动仍保留全部对称性约化收益。

`vasp_native_response.json` 分别保存电子/声子/总介电响应、钳制/离子/总压电
贡献和适用的弹性及 d 张量。低维结果明确标记为周期超胞响应，不直接称为本征
Bulk 常数。二维谱学的现有保护仍保留，待边界条件与转换完成验证后再开放。

## 具有压电响应的 AlN 案例

[纤锌矿 AlN 案例](../examples/VASP_Native_Response/AlN/README.zh-CN.md)
从结构优化开始，对比原生 DFPT 和原生应变有限差分，再计算 IR 及模式差分 Raman 谱。
验收包含独立压电分量 `e31`、`e33`、`e15`、介电闭合与 `e = d C`。
内部应变平移平衡不通过时保留原始张量并给出警告，不静默投影，
也不输出未经质量检查的 d 张量。保留的 PBE PAW 响应与谱学选择定则验收均通过：
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
zstar spectra job --root raman --system slurm --header header.sh --tasks 64 \
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
复用后的模式源采用新参考目录内的相对路径；移动谱学目录或移走原生响应目录
后，仍可独立完成后处理。

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
极化差分的几何修正。
输出 d 还要求内部应变平移平衡通过；缺失检查数据不能视为通过。电子和离子
压电贡献须同时存在；若 VASP 显式打印总压电张量，其与两项之和的差异须不超过
1e-4 C/m²。上述条件属于一致性检查，不能代替截断能、k 点及响应的收敛验证。
原生 JSON 与通用响应记录保存求解来源，区分原生 DFT、代数转换得到的 d 和
IR 后处理。检查失败时保留原始张量与原因，不静默切换算法或自动重跑。

## 作业头部

```bash
#!/usr/bin/env bash
#SBATCH --partition=hfacnormal01
#SBATCH --nodes=1
#SBATCH --ntasks=64
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
