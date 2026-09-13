---
name: develop-zstar-v2
description: Prepare, audit, and extend the ZStar v2 research response framework for electromechanical and higher-order materials responses; use for v2 theory, schema, symmetry reduction, validation, and case development, not ordinary v1 workflow execution.
metadata:
  short-description: Develop and audit ZStar v2 research workflows
---

# Develop ZStar v2

Use this skill only inside the isolated `zstar-v2-development` branch/worktree. The
stable v1 API, v1 cases, user manual, and v1 paper are read-only baselines. Do not
rename v1 paths, change `main`, publish packages/releases, or present a draft v2
module as a stable feature.

## Route v1 versus v2

- A request for BEC, Gamma phonons, dielectric, IR, or non-resonant Raman using
  the released workflow is a v1 task; use `run-zstar-workflows` and preserve its
  conventions.
- A request for strain/stress response, piezoelectric or elastic tensors,
  internal strain, phase/switching, finite-temperature interfaces,
  flexoelectricity, resonant Raman, or v2 schema/symmetry work is a v2 research
  task. Reuse v1 BEC/IFC/Gamma/PYATB capabilities; do not reimplement them.

## Minimum preflight

Before proposing a calculation or code change, inspect the structure and the
existing response record:

1. Determine dimensionality from the declared periodic axes and physical cell,
   not from vacuum alone. Reject molecular uniform periodic strain; restrict 2D
   and 1D responses to explicitly defined intrinsic directions and normalization.
2. Check atom ordering, lattice handedness, species, structure hash, expected
   space group, symmetry tolerance stability, and whether the system is insulating.
   A metallic Berry-polarization ensemble cannot enter the piezoelectric path.
3. Check the available calculator and assets (`ABACUS + PYATB` is the preferred
   validation route; VASP is an optional independent audit only when POTCAR and
   settings are reproducible). Do not infer a backend capability from a binary
   name alone.
4. Read the v2 `ResponseDocument` quantities and print units, axes, Voigt
   convention, ion-relaxation state, electrical/mechanical boundaries,
   `rank`, `residual`, condition number, and provenance before interpreting a
   tensor. Missing observations are not zeros.

## Build the smallest defensible plan

Write a short plan containing reference structure, independent symmetry-adapted
perturbations, positive/negative pairs, actual serialized strain/displacement,
one PYATB run per geometry for all a/b/c directions, expected outputs, and the
failure/restart condition. Use the symmetry input plan only after checking that
its allowed rank and selected-input rank are complete. A rank-deficient plan
must recommend additional paired directions; it must not zero-fill a tensor.

For real calculations, first run one smoke stage and obtain explicit human
confirmation before submitting a large ensemble. Use one `40 MPI x 1 OpenMP`
job per node only when that resource choice has been approved; after any launch
timeout, inspect the remote process group and stage lock before retrying. Never
blindly retry a remote runner.

## Interpret and gate results

- `e` is the proper strain-charge tensor at fixed electric field; retain raw
  Berry derivatives and Vanderbilt geometric corrections separately.
- `d`, `g`, and `h` are thermodynamic reciprocal forms with different electrical
  and mechanical boundary conditions. Derive them only from explicitly annotated
  proper `e`, `C^E`, and `epsilon^S`; do not substitute `e33` for `d33`.
- `C` must state stress sign, engineering/tensorial shear convention, units,
  major symmetry, eigenvalues, and energy/stress work-conjugacy diagnostics.
- `Lambda` must state its acoustic translation gauge and pass force-balance/
  acoustic-SR diagnostics before combining with BEC/IFC.
- Distinguish symmetry-forbidden components (exact representation constraint)
  from numerically small components (finite precision or sampling result).
- Label every output as `stable`, `research`, `conditional`, or `experimental`.
  Finite-temperature, flexoelectric, resonant-Raman, and switching paths remain
  experimental until their theory and independent validation gates are recorded.

Read [references/v2-response-gates.md](references/v2-response-gates.md) when a
task involves a new case, a rank/residual decision, low-dimensional boundaries,
or a proposed promotion from research to stable.

## Reproducibility handoff

Report the exact branch, code commit, input hashes, structure/symmetry result,
backend and version, functional, pseudopotential/orbital, k mesh, cutoff,
SCF/ionic thresholds, perturbation amplitudes, task count, node/MPI/OpenMP
layout, wall time/core-hours, output paths, rank/residual diagnostics, failed
and restarted stages, and the next gate. Keep temporary caches and large remote
outputs outside Git. Do not update the v1 paper or create a release as part of
v2 development.
