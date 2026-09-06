# Unified spectroscopy: bounded four-dimensional benchmark

Assembled measured components, not newly timed full workflows. Relaxation excluded. ABACUS+PYATB only; preparation excluded. Extra precision reference included conservatively. Reused-matrix PYATB timers include read-only provenance/hash checks. Cartesian optical reconstruction is verification cost, not new production cost. Old Raman computes both signs for all nonrigid modes, not a maximally symmetry-reduced mode baseline.

All four pairs use matched 40-core profiles.

Non-cubic-BaTiO3 retained BEC routes already requested forces. That output cost was not subtracted; independent force tasks supply the Separate phonons.

| System | IR SCFs: old/new | IR speedup | IR+Raman SCFs: old/new | Old core-h | New core-h | Ratio |
|---|---:|---:|---:|---:|---:|---:|
| HfO2 | 17/5 | 2.76 | 47/5 | 87.39 | 15.48 | 5.65 |
| MoS2 | 16/4 | 2.40 | 28/4 | 10.55 | 3.11 | 3.39 |
| Sb2S3 | 51/21 | 2.20 | 103/21 | 71.76 | 19.51 | 3.68 |
| CH4 | 16/4 | 3.98 | 34/4 | 27.88 | 3.34 | 8.35 |

HfO2 uses the completed matched control; its legacy 20-MPI result remains historical evidence.

| System | Atomic Cartesian tensor difference | Direct-mode tensor difference | Direct-mode absolute activity difference |
|---|---:|---:|---:|
| HfO2 | 0.01209% | 0.01818% | 0.02312% |
| MoS2 | 0.05514% | 0.0536% | 0.07765% |
| Sb2S3 | 0.02124% | 0.03575% | 0.02649% |
| CH4 | 2.337e-06% | 0.007653% | 0.01613% |

| System | IR mode-charge difference (common basis) | Maximum optical-frequency difference (cm^-1) |
|---|---:|---:|
| HfO2 | 0.005331% | 0.06869 |
| MoS2 | 0.7359% | 0.5269 |
| Sb2S3 | 0.008256% | 3.579 |
| CH4 | 0.001123% | 4.867e-06 |

Differences are relative L2 norms over all selected modes, not per-mode relative errors. Near-zero forbidden modes are retained. No independent curve normalization is used in the overlays.

IR overlays use each route's own Gamma frequencies. Raman overlays use the direct-control eigenbasis and frequencies to isolate the response-derivative comparison; they do not independently validate the phonon frequencies. Raw oscillator strengths, tensors, and activities accompany the curves.

CH4: six rigid motions are identified by mass-weighted overlaps; numerical rotational negative modes are recorded, not erased. Only positive internal vibrations enter these spectra.

No old relaxation/BEC/phonon SCF was repeated. New DFT: only 12 MoS2 + 18 CH4 + 30 HfO2 missing matched conventional Raman controls. Unified Raman reuses matrices with zero extra DFT.

Do not extrapolate these timings to resonant Raman, supercell phonon dispersion, or all materials. The reconstruction kernel is now part of the public Unified spectra lifecycle; see ../../unified_spectroscopy.md for reproducible commands.
