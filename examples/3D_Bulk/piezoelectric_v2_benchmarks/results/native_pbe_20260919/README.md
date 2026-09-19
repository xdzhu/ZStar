# Native VASP PBE response archive (2026-09-19)

This directory contains compact, license-safe result records for the accepted
symmetry-enabled AlN, GaN and ZnO native VASP calculations and the completed,
method-sensitive PTO calculation. It intentionally
does not contain POTCAR files, WAVECAR/CHGCAR files, raw OUTCAR files or scratch
directories. `completed.json` records the DFT job allocation; the tensor JSON
was regenerated from the retained raw output with post-processing commit
`c2346249` after the DFT calculation, without another VASP run.

Common settings are three-dimensional bulk PBE/PAW, 32 MPI ranks, one OpenMP
thread, `IBRION=6`, `ISIF=3`, `LEPSILON=.TRUE.`, `ISYM=2`, and `NCORE=1`.
The structural spglib/Phonopy tolerance is fixed at `1e-3 A` and is distinct
from VASP `SYMPREC`. AlN/GaN retain VASP's default `SYMPREC`; ZnO uses
`SYMPREC=1e-4` after an exact `P6_3mc` metric/Wyckoff projection that changes
the lattice and sites only at the `1e-5 A` serialization-noise scale.

| material | e31 | e33 | e15 | d33 | status |
| --- | ---: | ---: | ---: | ---: | --- |
| AlN | -0.581490 | 1.461400 | -0.309530 | 5.323688 | accepted |
| GaN | -0.264450 | 0.422860 | -0.146180 | 1.583054 | accepted; internal-strain decomposition warning retained |
| ZnO | -0.536880 | 1.042050 | -0.399280 | 9.750071 | accepted; internal-strain decomposition warning retained |
| PTO | 1.670070 | 2.439520 | 2.795970 | 63.994672 | internally closed; conditional because the independent 0.5% route gives d33=52.203773 |

`e` is in C/m2 and `d` is in pm/V (= pC/N). Acceptance of `d` requires a
mechanically stable relaxed-ion elastic matrix, elastic major symmetry,
electronic+ionic=total piezoelectric closure and `e=d C` closure. The raw
internal-strain translation diagnostic remains independent and is not silently
projected.

PTO additionally retains `independent_central_strain_005.json`, based on 13
structures at central engineering strain +/-0.5%, `ISYM=1`, and the exact P4mm
projection of the same parent POSCAR. All stages remain insulating, the maximum
force is `9.721e-5 eV/A`, the proper-e and elastic fits have relative residuals
0.477% and 2.138%, the symmetry residuals are 0.0187% and 0.0125%, and C is
positive definite. The serialized VASP stress antisymmetry is at most `2e-7`
kbar and is explicitly symmetrized under absolute and relative `1e-6` gates.
The 0.5% and native routes agree in C to 0.300% in Frobenius norm but differ in
e by 7.999% and in d by 8.838%; `d33` differs by 18.42% relative to the native
value. Therefore PTO is not promoted to the same cross-route validation status
as the three wurtzites, even though each route is internally self-consistent.

SHA256:

```text
AlN/completed.json 6e4c1e80b08a6e448ef19abcf6422b79782d27b8887933cdee2ed5a6937f3af0
AlN/vasp_native_response.json 43aed4290101d427709eab942a84ce7ff975694ae7b66ae02a23f83d29ee69fd
GaN/completed.json 2af4f740ddc4d2bfc7976a478c5d5acf05ab34d5526b9546cf9b7288e8b3d1a0
GaN/vasp_native_response.json 482e8c34852922a43b11801eb21d59f29147292b2a0353884cd37cc6d5e4cef1
PTO/completed.json f2a871a58b33a6236b73b92eb1c3272e39a3bdbcd3d48700982b22c97afe21fc
PTO/independent_central_strain_005_completed.json f600cbeb3b7d971235f2eb30a77bbd47dfef674df76a6651a8179f2d8ff1d848
PTO/independent_central_strain_005.json 820548aae82c454a88726988e69db3b714f0dcab483bd785529e4919a5bd3997
PTO/vasp_native_response.json 15319a80f0d0c705e048c8a21760701aefebc91f51a8a5ce0c7116e73d5b5042
ZnO/completed.json 7edd585f265b9cc7715a94509bc3f706aac518801cf733090d71b86105460782
ZnO/vasp_native_response.json 3a4525ad7939836dc1c5af3d87b4f8ca2fd273b58c5447bb4cf32097d9db9095
```

Detailed provenance and comparisons are in
`docs/development/vasp_native_aln_isym2_validation_20260919.md`,
`docs/development/vasp_native_gan_isym2_validation_20260919.md`, and
`docs/development/vasp_native_zno_exacthex_validation_20260919.md`. PTO's
cross-route qualification is documented separately because agreement, rather
than mere completion, is the unresolved scientific question.
