# qNEP 训练数据接口

GPUMD qNEP 是带动态电荷和长程静电作用的 NEP4 模型。训练时**不要求**提供
原子静态电荷标签；普通训练数据仍然是总能、逐原子力以及可选的 virial/应力。
逐原子波恩有效电荷是额外的可选监督量，在 extended XYZ 中写为 `bec:R:9`。

因此 ZStar 与 qNEP 可以自然衔接，但 BEC 不能替代能量、力和 virial 数据。
ZStar 的职责是给已有 NEP 数据集拼接 BEC，并审计这一对应关系。

## 给一个构型添加 BEC

```bash
zstar data qnep augment \
  --input train.xyz \
  --bec BEC.raw.dat \
  --frame 0 \
  --output train_qnep.xyz

zstar data qnep check --input train_qnep.xyz
zstar data qnep init --input train_qnep.xyz --output nep.in \
  --charge-mode 2 --lambda-z 0.5
```

`--bec` 可读取 `BEC.raw.dat`、Phonopy `BORN`、CP2K 的
`cp2k_bec.json` 或 VASP 的 `vasp_bec.json`。

## 多构型或部分构型带标签

GPUMD 官方允许仅为部分构型提供 BEC。可使用从零开始编号的 CSV：

```csv
frame,bec
0,labels/frame-0000/vasp_bec.json
25,labels/frame-0025/BEC.raw.dat
80,labels/frame-0080/cp2k_bec.json
```

```bash
zstar data qnep augment --input train.xyz --map bec_map.csv --output train_qnep.xyz
```

生成的审计 JSON 会记录每个带标签构型的 BEC 来源、原子数、张量变换和声学
和规则残差。若 BEC 文件包含元素信息，还会严格核对元素与原子顺序。

导出的 BEC 标签固定保留小数点后 10 位；统一的 `Z-BORN-*.out` 文件保留
小数点后 8 位，JSON 响应记录则保留可用的浮点精度。这是数据存储精度，不能
代替物理收敛性：仍需检查 SCF 阈值、位移大小、基组和采样参数。

## 导出稀疏 BEC 的 SCF 计算批次

BEC 有限差分流程中每一次 SCF 都已经产生真实的能量和力，因此都可以保留为
力场 E/F 数据；只有未位移母结构带 BEC。以下命令不以零矩阵伪造缺失标签：

```bash
zstar data qnep export \
  --input bec_force_only_raw.jsonl \
  --annotations all_bec_annotated.jsonl \
  --output multiphase_pbesol_raw.xyz
```

`--annotations` 按母结构 `frame_id` 匹配。ZStar 会把晶相标签继承到位移子帧，
仅在 `PARENT::0.no-move` 写入 BEC；同时按周期性位置匹配并重排原子，避免
ABACUS 与 extxyz 的氧原子顺序不同而静默错配。审计文件会分别记录有/无 BEC
的帧数，原始能量和力不会被改写。

为检查加入其他晶相是否影响固定 cubic 基准集，可做确定性的分层拼接：

```bash
zstar data qnep compose \
  --base cubic_full.xyz \
  --addition multiphase_pbesol_raw.xyz \
  --phases tetragonal orthorhombic rhombohedral \
  --max-per-phase 108 --seed 20260915 \
  --output cubic_plus_balanced_phases.xyz
```

该操作按 `frame_id` 去重，保留被选中 extxyz 帧的原始内容并输出审计记录。
若把 `cubic_full.xyz` 同时用于训练和测试，得到的只能称为 **cubic 全集的
in-sample 拟合误差**，不能称为无泄漏泛化误差。训练完成后可由：

```bash
zstar data qnep score --test cubic_full.xyz --directory qnep_run
```

计算 E/F/BEC parity 指标。BEC 统计只使用测试集实际带 `bec:R:9` 的原子，不会
把 qNEP 为未标注原子输出的零占位符当作参考 BEC。

## 张量约定与科学限制

GPUMD 将 `bec:R:9` 按行优先保存，其中行对应电场/极化方向，列对应力/位移
方向，与 `F_j = sum_i E_i Z_ij` 一致。ZStar 统一文件使用位移为行、极化为列，
因此导出器会明确转置。若直接把九个分量原样拼接，非对角分量可能被静默交换。

qNEP 在使用 BEC 监督时假设整个训练集采用同一个高频介电常数，所以官方文档
提醒：BEC 监督通常只适用于同一种材料的同一个相。不要把不同化学体系、不同相、
不一致的 DFT 设置、原子顺序、极化分支或介电屏蔽混入同一个 BEC 监督模型。

因此，多晶相 BaTiO3 训练只能作为兼容性和覆盖率诊断，不能替代面向单一晶相的
生产级 qNEP。其 E/F/BEC 应来自已声明的统一计算设置（例如同一 PBEsol
赝势、轨道和基组）；绝不能静默混入采用其他泛函得到的公开参考标签。

GPUMD 对所有方向都采用周期边界。分子和二维数据必须专门设计周期盒与截断半径，
不能把真空层当成非周期边界。

官方资料：[GPUMD `train.xyz` 格式](https://gpumd.org/nep/input_files/train_test_xyz.html)、
[`charge_mode`](https://gpumd.org/nep/input_parameters/charge_mode.html)、
[`lambda_z`](https://gpumd.org/nep/input_parameters/lambda_z.html) 和
[qNEP 论文，DOI 10.1021/acs.jctc.6c00146](https://doi.org/10.1021/acs.jctc.6c00146)。
