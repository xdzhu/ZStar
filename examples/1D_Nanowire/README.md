# One-dimensional BEC examples / 一维材料

| Case | Purpose / 用途 |
|---|---|
| [BN_9_0](BN_9_0/) | Unpassivated PBE BN(9,0) nanotube / 无需钝化的氮化硼管 |
| [Sb2S3](Sb2S3/) | PBE-D3(BJ) isolated chain / 孤立链 |
| [GaAs_nanowire](GaAs_nanowire/) | Earlier passivated-wire example, not a paper benchmark / 早期钝化案例 |

The first two cases use centered transverse vacuum and the unified BEC/Gamma
workflow. Each has `run/`, `results/`, and `run.sh`. The default runner computes
the displacement response without repeating Raman calculations.
前两个案例均已在横向真空居中；默认入口只运行 BEC/力常数，不重复 Raman 计算。

Full spectra remain in [IR_Raman_Spectra](../IR_Raman_Spectra/).
完整光谱保留在独立的谱学案例目录。
