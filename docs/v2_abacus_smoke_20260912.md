# ZStar v2 ABACUS 应变 smoke test（2026-09-12）

**状态：** Gate C 前置 smoke；不是最终弹性 benchmark。
**分支：** `zstar-v2-development`；应变准备代码提交 `9369de2`。
**远程临时目录：** `/home/zhuxd/zstar_v2_smoke_20260912/strain2`（不在 Git 中）。

## 输入和环境

* 结构：cubic BaTiO₃，5 原子 primitive cell；来自
  `examples/3D_Bulk/cubic_BaTiO3/phonon_spectrum/run/STRU`。
* 泛函/截断：PBEsol、LCAO、`ecutwfc=100`；`KPT=9 9 9 0 0 0`。
* ABACUS：v3.10.0，commit `e84abb4`；每个节点只运行 1 MPI process、1 OpenMP thread，
  没有超过用户占位作业的 40 核边界。
* 每个阶段由 v2 generator 私有复制 `STRU/INPUT/KPT` 和 PP/ORB，并强制写入
  `cal_force=1`、`cal_stress=1`；实际序列化应变保存于 `ensemble.json`。

## 阶段结果

| 阶段 | 节点 | 实际 `eta_xx` | SCF `E_Harris` 行数 | 收敛 | `TOTAL-STRESS` | wall time |
|---|---|---:|---:|---|---|---:|
| reference | cu24 | 0 | 12 | yes | yes | 131 s |
| strain-001- | cu25 | -0.00100000000000022 | 12 | yes | yes | 131 s |
| strain-001+ | cu26 | +0.00099999999999967 | 12 | yes | yes | 132 s |

ABACUS 原始应力（KBAR，保留原符号）为：

```text
reference:  diag( 0.3748412154,  0.3748412154,  0.3748412154 )
strain - :  diag( 3.6004660309,  1.4926137776,  1.4926137776 )
strain + :  diag(-2.8185879742, -0.7383655290, -0.7383655290 )
```

按 `(+ - -)/(eta_+ - eta_-)` 定义，这一个中心差分给出的 backend-raw 斜率为
`d sigma_xx/d eta_xx≈-320.9527 GPa`、`d sigma_yy/d eta_xx≈-111.5490 GPa`；
它尚未通过 ABACUS 应力符号、有限应变定义、收敛扫描和独立后端验证，不能写入正式
弹性常数。若后续确认该后端采用 compression-positive，adapter 才能显式翻转为
tension-positive，而不是在解析阶段静默改号。

## 失败—修正证据

第一版参考单点故意保留 `STRU` 中的资产文件名但没有把 `assets/` staging 到工作目录，
ABACUS 以 `RC=1` 清晰报告缺少 orbital。修正 generator 后，三阶段均 `RC=0`，并出现
`TOTAL-STRESS (KBAR)`。这验证了资产隔离和 stress capability gate；没有把失败静默成零。

## 可复现命令（远程）

```bash
ssh cu24 'cd /home/zhuxd/zstar_v2_smoke_20260912/strain2/reference && \
  OMP_NUM_THREADS=1 /home/zhuxd/Software/abacus/INSTALL/3.10.0-LTS/bin/abacus'
ssh cu25 'cd /home/zhuxd/zstar_v2_smoke_20260912/strain2/strain-001- && \
  OMP_NUM_THREADS=1 /home/zhuxd/Software/abacus/INSTALL/3.10.0-LTS/bin/abacus'
ssh cu26 'cd /home/zhuxd/zstar_v2_smoke_20260912/strain2/strain-001+ && \
  OMP_NUM_THREADS=1 /home/zhuxd/Software/abacus/INSTALL/3.10.0-LTS/bin/abacus'
```

本轮只完成单一 xx 应变的三阶段 smoke；尚未进行完整六分量、多个幅度、relaxed-ion
弛豫、极化收集或独立后端交叉验证。
