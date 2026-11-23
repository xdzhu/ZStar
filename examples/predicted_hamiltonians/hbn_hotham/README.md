# Hot-Ham ABACUS export for monolayer hBN

This example checks Hot-Ham's real spin-degenerate LCAO export on the
26-orbital hBN cell in `../hbn`. The native files in `export.zip` contain
the inferred H, exported overlap, separately exported reference H, and
prediction geometry. All three matrices use 81 lattice translations.

We used the [upstream Hot-Ham code](https://github.com/liangzhixin-202169/Hot-Ham/tree/7518adfe2cd1405de452eda362e45e55b522a836)
on CPU. One model was fit to the archived `disp-006` ABACUS H. Its
prediction dataset for `disp-005` contained only the geometry and
ABACUS S. Both elements used the 10 Bohr 2s2p1d numerical basis. Training
used 200 epochs, seed 42, initial learning rate 0.01, L_max 4, radial cutoff
12.1 Å, first_channel 8 and mid_channel [8, 8]. In a separate control export
Hot-Ham read the original `disp-005` H and wrote `h_ref_0.csr`.

From a clean directory, with ZStar installed, unpack the two archives.
Set `examples` to the absolute path of `examples/predicted_hamiltonians`.

```sh
python -m zipfile -e "$examples/hbn/pyatb_inputs.zip" .
python -m zipfile -e "$examples/hbn_hotham/export.zip" .
python "$examples/hbn_hotham/check_export.py"
```

| Check on disp-005 | Result |
| --- | ---: |
| Largest overlap entry error | 1.50 × 10⁻⁸ |
| Largest reference-H round-trip error | 1.00 × 10⁻⁷ Ry |
| Largest predicted H(R) − H(−R)ᵀ entry | 0 Ry |
| Predicted indirect gap | −3.366337 eV |
| ABACUS indirect gap | 4.671978 eV |

The gap uses four occupied bands on the 36 × 36 × 8 Berry mesh. The
single-frame fit gives overlapping valence and conduction bands at
different k points. A bulk insulating polarization for this prediction
is therefore undefined. The original ABACUS Hamiltonian has an insulating
gap and permits a solver check using its Hot-Ham reference export.

Install ASE for the extended XYZ reader (`pip install 'zstar[hotham]'`).
From the same directory, replay that **reference control** with PYATB.

```sh
zstar response pyatb-hamiltonian --model hotham \
  --input disp-005/reference/Input --structure disp-005/common/STRU \
  --prediction-structure model.xyz --hamiltonian h_ref_0.csr \
  --model-overlap olp.csr --fermi-energy -2.47153268223 --output-dir reference-export
(cd reference-export && pyatb)
```

PYATB 1.1.1.dev0+b3c70a1 printed −0.000353 C/m² along c for the
reference export, matching the [native ABACUS control](../hbn/results/berry-controls/disp-005/reference/Out/Polarization/polarization.dat)
in all three directions to the printed precision. For an insulating model
prediction, use its `h_pred_0.csr` and a Fermi energy inside its gap as
shown in the [input guide](../../../docs/predicted_hamiltonians.md#hot-ham).
