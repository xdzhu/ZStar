# 与带电荷机器学习力场的兼容性

ZStar 可以为带电荷机器学习力场准备和审计与计算器无关的参考数据，
但不负责训练力场。数据集可以让所有 frame 都有能量、力和应力/virial，
而只为温度和晶相分层选择的代表性子集计算 BEC。缺失 BEC 使用
`null + born_effective_charges_available: false` 显式表示，不能用零矩阵代替。

```text
zstar data inspect  --input dataset.jsonl
zstar data select   --input dataset.jsonl --output selected.jsonl --count 64 --seed 7 --temperature-bin 300 --temperature-bin 500
zstar data annotate --input selected.jsonl --map frame_bec.csv --output labeled.jsonl
zstar data validate  --input labeled.jsonl --report validation.json
zstar data export    --input labeled.jsonl --output train.xyz
```

也支持直接读取标准 DeepMD `deepmd/npy` 数据集，不要求安装 `dpdata`：

```text
zstar data inspect --input deepmd_npy/ --metadata frame_metadata.csv
zstar data select --input deepmd_npy/ --metadata frame_metadata.csv \
  --output selected.jsonl --count 100 --seed 17 \
  --temperature-bin 300 --temperature-bin 500
```

读取器支持 `set.*`、`coord.npy`、`box.npy`、`energy.npy`、`force.npy`、可选
`virial.npy`、`type.raw` 和 `type_map.raw`。温度和晶相不从目录名猜测，而是
通过显式 CSV 提供。选出的 JSONL frame 可以进入现有 BEC workflow，再用
`zstar data annotate` 回填 BEC。sidecar 还可以显式提供 `total_charge` 和
`split` 列，以保留电荷态以及 train/validation/test 划分。

如果稀疏标注只需要 BEC 张量而暂时没有 PYATB 光学/静态介电输出，统一收集器
可以使用 `zstar deal --pyatb --bec-only`。该模式写出 `BEC.dat`、
`BEC.rep.dat` 和响应诊断；但要生成 NAC/BORN 声子输入，仍必须提供静态介电数据。

同一入口也接受 ASE extended-XYZ 数据集，包括常见的 MACE
`REF_energy`、`REF_forces` 和 `REF_stress` 字段。DeepMD、MACE 及其他力场格式
只是源数据适配器；代表性结构选出后，统一调用同一套 DFT/BEC 工作流，不为每个
力场重复实现 BEC 计算。

包含 `STRU` 和 `OUT.*` 的 ABACUS 计算目录也可以通过可选的 `dpdata` 适配器
读取能量、坐标、力和 virial；BEC 仍由 ZStar/PYATB 响应工作流单独回填。
普通 ZStar 安装不强制依赖 `dpdata`。

BEC 有限位移工作流中的每个完整 SCF（也就是这组响应计算中已经支付的
`N_SCF` 个自洽步骤）本身也有能量和原子力，因此可以复用为
小型的“仅力”辅助数据集。`examples/.../run/collect_bec_batch.py
--force-only-output` 会提取 `0.no-move` 和 `disp-*` 的 SCF 能量/力，但仍将这些
行的 BEC 明确保持为缺失；每行记录 `parent_frame_id`、位移编号/向量和 SCF
来源。只要一个位移成员未完成，就拒绝整个 family，避免产生看似完整的部分
数据。由于这些位移帧彼此相关，训练/验证/测试必须按母帧切分。最终乌镇批次从
65 个完整母帧得到 612 个辅助能量/力 frame；原始 JSONL 保留在 scratch，仓库只记录
中性 manifest。未完成的母帧不补零，也不作为独立验证集，不能替代统一设置生成的
r2SCAN 能量/力/virial 数据池。

生成的仅力 JSONL 可以沿用同一导出路径：
`zstar data export --input force_only.jsonl --output force_only.xyz`，再用
`zstar qnep check` 审计；该辅助文件的 BEC 标签数为零是预期行为。

本兼容性示范建议将力场数据集控制在约 200--500 帧，选择约 50--100 帧计算
BEC。这足以展示数据准备、稀疏响应标签和下游声子/NAC 检查，不以建立生产级
qNEP 精度为目标。

当前 cubic-BaTiO3 示例采用已经完成的 ABACUS/PBEsol DFT 结果：169 个唯一
结构（119 个 5 原子原胞、50 个 2×2×2 大胞），其中 2 帧带 BEC、167 帧显式
缺失 BEC。数据收集直接复制已有 `FINAL_ETOT_IS`、力和结构标签，不做能量
平移、归一化，也不重新提交旧 DFT。旧的
`qnep_export/train_qnep_249_sparse62.xyz` 仅作为公开格式解析夹具，不能用于
最终精度或声子结论。
65 个完整 primitive/displacement 母帧提供 BEC 来源；公开数据没有可信的逐帧 MD
温度，因此不虚构温度，也不默认把 120 原子超胞送入会产生数百个位移任务的 BEC 队列。

格式记录稳定的 frame ID、结构 ID、原子顺序、晶胞/坐标、总电荷、可选的
极化/偶极/BEC、温度、晶相、单位、坐标约定、计算器和 DFT 来源。BEC 形状
为 `(N_atoms, 3, 3)`，单位为元电荷。导出 qNEP 时显式转换 ZStar 的位移行
约定到 GPUMD 的电场行 `bec:R:9` 约定，同时保留未标注 frame。

qNEP 是一个实际兼容性示例：qNEP/GPUMD 提供动态 partial charge、电荷守恒和
长程静电，ZStar 提供结构及可选 BEC 参考响应。仓库中的 Level 2 小规模
benchmark 会调用外部 GPUMD `nep`/`gpumd` 可执行程序；ZStar 核心本身不训练
qNEP、不运行 GPUMD 分子动力学，也不替代 Phonopy 或 DYNASOR。温度依赖极化、介电常数、
P–E 回线和频率相关介电函数仍需要训练好的模型、长时间 MD 轨迹和外部后处理。
