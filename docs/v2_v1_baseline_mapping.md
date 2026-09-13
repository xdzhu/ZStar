# v1 → v2 基线映射

本文件用于防止 v2 重复实现 v1 已完成的物理链路。状态分为：

- **继承**：直接使用 v1 结果、算法或接口，并保留 v1 回归；
- **适配**：只增加 v2 的单位、边界、坐标、provenance 或 schema 包装；
- **新增**：v1 没有的应变响应或任意空间群算法；
- **待核验**：物理链路已存在，但当前 v2 证据尚未覆盖某个后端或边界条件。

## 基线矩阵

| 能力 | v1 权威实现/资产 | v2 处理 | 当前状态 |
|---|---|---|---|
| Berry 极化与三方向 PYATB 输出 | `zstar/shared_response.py`、现有 PYATB precision writer 与案例 | `zstar/v2/polarization.py` 只负责解析、分支匹配和 calculator-neutral 记录 | 继承 + 适配 |
| BEC / Born 张量 | v1 Unified BEC、`zstar/vasp_bec.py`、`zstar/cp2k_bec.py`、既有 `BORN/BEC` 资产 | v2 只消费既有张量，检查轴序、单位、声学和 provenance | 继承 + 回归 |
| Gamma 声子与 IFC | `zstar/shared_response.py`、`zstar/phonon_post.py`、Phonopy 输出 | v2 不重写 Gamma/IFC；应变响应只新增 \\(\\Gamma_{u\\eta}=-\\partial F/\\partial\\eta\\) 拟合 | 继承 + 新耦合块 |
| Acoustic sum rule / 平移规范 | v1 Phonopy/统一响应检查 | `zstar/v2/algebra.py` 提供显式诊断和可选拒绝门，不隐式投影 | 继承 + 适配 |
| \\(Z^*\\Lambda\\) relaxed-ion 装配 | v1 已有响应代数和物理定义 | v2 仅增加长度/体积单位、轴序、边界条件和结果封装 | 继承 + 适配 |
| 应力 work-conjugacy | v1 应力/能量约定 | v2 明确 tension/compression sign、engineering strain 与 tensorial stress Voigt 表示 | 兼容性审计 |
| 应变生成 | v1 没有统一 electromechanical ensemble | `zstar/v2/strain.py` 使用实际序列化应变向量、正负中心差分和 restart | 新增 |
| 应变—力耦合 \\(\\Gamma_{u\\eta}\\) | v1 没有该响应块 | `fit_strain_force_coupling` 使用首个固定离子力块拟合 | 新增 |
| 压电/弹性有限差分封装 | v1 没有 v2 schema/边界字段 | `fit_response_document` 只拟合已有观测，不补零、不猜 stress sign | 新增 |
| 任意空间群响应约化 | v1 主要服务 BEC/Gamma 位移集合 | `zstar/v2/structure.py`/`symmetry.py` 扩展到 polarization/force/stress/displacement 表示与 rank | 新增 |

## 关键语义区分

`Gamma` 在两个地方含义不同：v1 的 Gamma phonon/IFC 是位移—位移二阶响应；
v2 新增的 \\(\\Gamma_{u\\eta}\\) 是原子力对应变的一阶导数。二者通过
\\(\\Phi\\Lambda\\) 发生代数联系，但不能把一个张量直接当成另一个张量。

同理，v2 的 `relaxed_piezoelectric` 和 `relaxed_elastic` 不是重新发明 v1 理论，
而是把已知关系包装成显式单位和 acoustic-gauge 输入。若 v1 结果已经满足相同
坐标、符号、单位和边界条件，v2 应导入其 provenance 并回归，而不是重复计算。

## 当前真正缺口

1. v1 结果到 v2 `ResponseDocument` 的 provenance 映射仍需冻结；
2. VASP 的应变力/应力 collector 和 POTCAR 输入一致性尚未验证；
3. stress work-conjugacy 需要把既有 v1 证据映射到 v2 的 engineering-Voigt 契约；
4. 低对称真实材料与二维归一化仍未完成 v2 证据闭合。

这些是接口、证据和覆盖范围问题，不是重新开发 BEC、Gamma phonon 或已有 PYATB
极化算法的问题。
