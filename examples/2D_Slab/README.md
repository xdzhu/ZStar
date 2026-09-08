# Slab BEC examples / 二维材料

Run each case from its own directory: `bash run.sh --dry-run`, then follow its
README to configure ABACUS/PYATB and execute `bash run.sh`. Inputs and retained
outputs are separated into `run/` and `results/`.
先检查案例 README 与试运行输出，再执行计算；不要把不同泛函或结构的结果混用。

| Case | Purpose / 用途 |
|---|---|
| [hBN](hBN/) | Monolayer hybrid in-plane/out-of-plane BEC / 单层混合极化路线 |
| [hBN_unified](hBN_unified/) | Unified/Separate matched benchmark / 同设置对照 |
| [In2Se3_PBEsol](In2Se3_PBEsol/) | PBEsol monolayer literature comparison / PBEsol 文献对照 |
| [alpha_In2Se3_PBE](alpha_In2Se3_PBE/) | Separately relaxed PBE unified benchmark / PBE 效率对照 |
| [In2Se3](In2Se3/) | Retained hybrid-response example / 混合响应示例 |
| [MoS2](MoS2/) | Retained slab BEC example / 二维 BEC 示例 |
| [MoS2_unified](MoS2_unified/) | Unified/Separate benchmark and mesh controls / 网格与效率对照 |

The spectroscopy-matched MoS2 BECs are also retained with
[IR/Raman data](../IR_Raman_Spectra/2D_MoS2/).
与归档光谱一致的 MoS2 BEC 位于上述谱学案例中。
