# v2 压电验证候选材料（3D、结构简单）

本文档只冻结“候选与文献锚点”，不表示已经完成这些材料的 v2 计算。
候选选择遵循：三维体相、绝缘、原胞小、空间群明确、存在可核验的原始理论或
实验数据、并且能检验 v2 的不同张量约化分支。计算前仍需固定泛函、晶格参数、
极化分支、proper/improper 约定、Voigt 工程剪切和 clamped/relaxed-ion 边界。

## 推荐顺序

**第一优先：wurtzite ZnO；第二优先：wurtzite AlN；第三优先：zinc-blende GaAs。**

ZnO 和 AlN 都是两原子、`P6_3mc`、点群 `6mm`，可以直接复用 GaN 的三维六方
响应协议，但材料离子性、内部应变贡献和响应大小不同；这样不是重复造轮子，而是
检验同一算法在不同化学键合下是否仍成立。GaAs 是两原子、`F-43m`、点群
`\bar{4}3m`，体相只有一个独立的剪切压电常数 `e14`，可独立审计 cubic 的
工程剪切、坐标手性和符号约定。

| 优先级 | 材料/结构 | 原胞与对称性 | 适合验证的独立量 | 已核验文献锚点（数值） | 主要风险 |
|---|---|---|---|---|---|
| 1 | ZnO wurtzite | 2 原子；`P6_3mc` / `6mm` | `e33`, `e31`, `e15`；BEC、内部应变；由 `e C^{-1}` 得 `d33` | Dal Corso 等给出 Berry-phase `e33=0.92`、`e31=-0.39 C m^-2`（其 LDA/实验结构定义）；Gopal–Spaldin 的 SIC-DFT 给出 relaxed `e33=1.34`、`e31=-0.57 C m^-2`；同一来源报告 `P=-0.05 C m^-2` | Zn 3d 半芯态、LDA/SIC/PBE 差异；文献晶格参数和符号轴必须一致；`e15` 需使用完整张量来源，不可由 `e31/e33` 猜测 |
| 2 | AlN wurtzite | 2 原子；`P6_3mc` / `6mm` | 与 GaN 相同的三分量及 `d31,d33,d15`；弹性-压电互逆 | Bernardini–Fiorentini–Vanderbilt：`e33=1.46`, `e31=-0.60 C m^-2`，`P=-0.081 C m^-2`；实验 `e33=1.55`, `e31=-0.58`，误差约 5%；Zoroddu 等 GGA：`e33=1.50`, `e31=-0.53`, `C33=377`, `C31=94 GPa`；直接 stress-piezo GGA `d31=-2.1`, `d33=5.4`, `d15=2.9 pm/V` | `d` 对 LDA/GGA 和 clamped/free-standing 条件敏感；`e31` 的 proper/improper 需明确；文献实验多为薄膜或夹持转换 |
| 3 | GaAs zinc-blende | 2 原子；`F-43m` / `\bar{4}3m` | 仅 `e14=e25=e36`；剪切应变、cubic 旋转和符号 | McKitterick 的原始有限波矢第一性原理研究给出介电、有效电荷和压电常数并与实验比较；工程/器件文献采用单晶实验 `e14≈-0.16 C m^-2`；现代 GGA 计算在过大的晶格常数下得到 `e14=-0.342 C m^-2`，作者明确提示该几何导致精度问题 | `e14` 对晶格常数和符号手性敏感；不能把 `e14` 直接等同于六方 `e33`；实验值需要注明温度和取向 |
| 4 | ZnS（wurtzite 或 zinc-blende） | 2 原子（原胞表示依多型而定） | 与 ZnO 同族但响应较小；检验内部应变-电子项抵消 | Catti–Noel–Dovesi 计算了 ZnO/ZnS 两种多型的完整 proper `e`、`d` 和弹性张量，并显式包含 wurtzite `e15` | wurtzite ZnS 常为亚稳多型；实验单晶锚点少，适合作为第二批而非首批门槛 |
| 5 | BaTiO3 tetragonal | 5 原子；`P4mm` | 铁电极化、软模、`e/d` 与 phase/switching 的接口 | 现有仓库已有 `P4mm` 算法 fixture；其材料常数强烈依赖相、应变和泛函 | 软模和多相性使结果不适合作为首个跨材料数值门；应在二元半导体闭环后再做 |
| 6 | 3C-SiC zinc-blende | 2 原子；`F-43m` / `\bar{4}3m` | `e14`、立方剪切、弹性；与 GaAs 比较化学趋势 | 3C-SiC 没有反演中心，群论允许一个独立压电分量；它不是零压电 control | 必须与中心对称 diamond Si 分开，不得从“立方”误推“压电为零” |
| 7 | diamond Si | 2 原子；`Fd-3m` / `m\bar{3}m` | 中心对称零压电 control、弹性与 forbidden-component 审计 | 反演对称严格禁止线性压电张量 | 数值近零与群论严格禁止必须分别报告 |
| 8 | PbTiO3 / ordered PZT 50/50 | PT: 5 原子 `P4mm`；PZT: [001] 1:1 B-site ordered 10 原子 `P4mm` | 四方 `e31/e33/e15`、极化软模及构型敏感性 | Sághi-Szabó、Cohen 和 Krakauer以 GGA/Berry phase 比较了 PT 以及 [001]/[111] 有序 PZT50/50 的 proper `e`；[001] 有序增强 `e33` | PZT 不是唯一结构；组分、B 位有序、温度及 `P4mm/Cm/R3m/R3c` 相必须显式标注 |

## 具体比较协议

1. **先做 ZnO，再做 AlN。** 两者均采用三维 primitive wurtzite、`z || [0001]`，
   保留完整六方晶格。每个 `+/-` 应变几何只运行一次 PYATB，从同一输出读取三个
   Berry 极化方向；禁止用三次 ABACUS NSCF 代替 v1 的极化路径。
2. 对每个材料同时保存 clamped-ion 与 relaxed-ion 结果，并单独记录 `Lambda`、
   BEC、弹性 `C`、proper/improper 修正和 `e -> d` 回算。`d` 的文献比较只能在
   固定应力/应变边界、单位 `pm/V = pC/N` 和剪切约定一致时进行。
3. **再做 GaAs。** 只需检验 cubic `e14` 的一个独立分量及其对称补全，但必须使用
   真实序列化应变向量和中心差分，报告 `rank/residual` 以及三个等价分量的最大
   不一致度。
4. 低维 hBN、MoS2、In2Se3 暂不进入这一轮：二维“每面积”与真空归一化、开放方向
   电边界尚未达到稳定 benchmark 条件。BeO 可作为低响应/争议性负对照，但不应替代
   ZnO/AlN 的主验证。
5. PZT 第一轮只计算 `PbZr0.5Ti0.5O3` 的 [001] 1:1 B 位层状有序 `P4mm` 10 原子
   模型。经典 GGA/Berry-phase 工作使用同类 [001] 与 [111] 显式有序模型；后续
   `Cm` MPB 结构和六种 2x2x2 B 位构型属于独立的构型/相敏感性研究，不能与首个
   模型平均成一个所谓“PZT 压电常数”。

## 文献数值的使用边界

文献数值是外部锚点，不是无条件的“正确答案”。不同论文使用的 LDA、GGA、SIC、
实验晶格、应力夹持和极化轴定义不同；v2 报告必须逐项写出结构、泛函、坐标手性、
Voigt 约定、proper/improper、clamped/relaxed-ion 和温度。若只找到 `e33/e31` 而
没有同一约定下的 `e15` 或完整弹性矩阵，则只能做部分比较，不能声称“完整张量验证”。

## 进入计算的门槛

* 结构在目标泛函下绝缘，空间群识别稳定，且微小扰动不会误把不等价原子合并；
* 文献锚点与计算轴、单位和边界条件完成映射；
* 先用单个 `+/-` 应变 smoke test 检查 Berry 分支和三方向极化，再扩展到完整
  symmetry-adapted ensemble；
* 只有 rank、residual、张量对称性、机械稳定性和 `e C^{-1}` 互逆均通过，才将结果
  写入案例 `results/` 并用于论文。
