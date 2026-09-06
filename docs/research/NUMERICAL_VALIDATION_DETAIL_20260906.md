# Retained numerical validation details

Moved from the manuscript appendix; these observations remain part of the reproducibility record.

```latex
\subsection{Numerical reconstruction and convergence}
The original Cartesian joint-response controls isolate the effect of changing the displacement ensemble. They are not the independent force workflows used in the final efficiency table. For the seven stable bulk, sheet, and molecular controls, the maximum force-component difference from the corresponding Unified stages was $6.42\times10^{-6}$~eV/\AA{}. Combining those independent force fits with the retained Cartesian BECs gives the direct Separate--Unified comparison in Table~\ref{tab:separate_accuracy}. All seven pass the optical-subspace check. The larger MoS$_2$ difference is dominated by the baseline Berry integration, as discussed below; it is not removed by rerunning forces. The additional one-dimensional checks are reported separately below.

\begin{table}[htbp]
\centering\small
\caption{Relative differences of the static phonon response between the measured Separate and Unified workflows, $\|R_{\mathrm S}-R_{\mathrm U}\|_F/\|R_{\mathrm S}\|_F$. $R$ is the bulk phonon permittivity, sheet phonon polarizability, or fixed-orientation molecular vibrational polarizability. Baseline Berry meshes are used. Cubic BaTiO$_3$ is excluded because its reference is unstable.}
\label{tab:separate_accuracy}
\begin{tabular}{lr}
\toprule
System & Relative difference (\%) \\
\midrule
3C-SiC & 0.00143 \\
t-HfO$_2$ & 0.0259 \\
$\alpha$-In$_2$Se$_3$ & 0.0519 \\
hBN & 0.0434 \\
MoS$_2$ & 1.46 \\
H$_2$O & 0.0153 \\
CH$_4$ & 0.00188 \\
\bottomrule
\end{tabular}
\end{table}

The following reconstruction and refinement results instead compare the original Cartesian joint-response and Unified ensembles, including both independent BEC and Hessian reconstructions.
The cubic BaTiO$_3$ comparison has a maximum raw BEC difference of $3.76\times10^{-4}\,e$, a maximum frequency difference of 0.041~cm$^{-1}$, and a relative raw-Hessian difference of 0.0592\%. The unstable optical triplets occur at $217.8i$~cm$^{-1}$ in both routes. For SiC, tetragonal HfO$_2$, and hBN, the maximum raw BEC differences are $2.14\times10^{-5}$, $5.15\times10^{-4}$, and $8.46\times10^{-4}\,e$, respectively; the frequency differences are 0.010, 0.069, and 0.436~cm$^{-1}$. The relative static phonon-response differences are 0.00103\%, 0.0589\%, and 0.0209\%. These are matched-setting numerical differences, not errors against experiment.

For In$_2$Se$_3$, the PBE reference follows the FE-ZB$'$ stacking and numerical settings of Ding \textit{et al.}\ \cite{Ding2017}: a $\Gamma$-centered $12\times12\times1$ SCF mesh, more than 15~\AA{} of vacuum, a slab dipole correction, and a force threshold of 0.005~eV/\AA{}. ABACUS ONCV/LCAO replaces that work's VASP PAW basis. Following cell relaxation, a recorded numerical shear below $10^{-4}$~\AA{} was removed and the ions were relaxed again. The final $P3m1$ structure has $a=4.104$~\AA{}, a band gap of 0.780~eV, and a maximum residual force of 0.0036~eV/\AA{}. This convergence benchmark is distinct from the PBEsol BEC literature comparison.

Refining the In$_2$Se$_3$ Berry mesh from $22\times22\times2$ to $88\times88\times2$ reduces the largest raw BEC difference from $9.30\times10^{-3}$ to $1.54\times10^{-3}\,e$. A symmetry-forbidden transverse residual also decreases, showing that a predominantly normal mixed displacement can amplify in-plane integration noise. However, the static phonon-response difference changes only from 0.802\% to 0.799\%. To identify its origin, we recombined the two BEC and Hessian datasets at the same geometry. At the refined mesh, changing only the Hessian gives a 0.746\% relative response change, while changing only the BEC gives 0.0513\%. The lowest optical pair at 17.8~cm$^{-1}$ makes the response sensitive to force and displacement errors through the $1/\omega^2$ factor. The approximately 1.1\% change on halving the unified displacement confirms this sensitivity; improving Berry integration alone cannot remove it.

MoS$_2$ exhibits a different balance. At the default $28\times28\times2$ Berry mesh, the maximum raw BEC difference is $6.41\times10^{-3}\,e$, the maximum frequency difference is 0.527~cm$^{-1}$, and the static phonon sheet-response difference is 1.75\%. Exchanging only the BEC gives a 1.46\% change, compared with 0.291\% from exchanging only the Hessian. A polarization-only refinement to $112\times112\times2$, using unchanged SCFs, forces, cube dipoles, and reference electronic response, lowers the raw BEC difference to $1.72\times10^{-3}\,e$ and the static difference to 0.520\%. The refinement is retained separately from the baseline efficiency measurement and does not replace the archived spectroscopy dataset.

Independent Phonopy fits agree with the reconstructed raw force Jacobians after matching the combined atom and Cartesian index convention. For stable periodic references, the mode sum and Hessian-inverse static response agree within $3\times10^{-7}$ in relative norm in the original three-system check. These algebraic checks do not remove finite-displacement or DFT convergence errors. The archives retain raw force sums, charge sums, reciprocity residuals, and the corrections applied during projection. Analytic tests cover all 32 crystallographic point groups, mixed displacement directions, atomic permutations, nonsymmetric BEC tensors, and rank-deficient inputs. No fixed two-displacement reduction is assumed for arbitrary symmetry.

For the molecular benchmark, the raw Cartesian Hessian is retained and an independent mass-weighted internal-coordinate audit removes rigid translation and rotation about the center of mass. The remaining $3N-6$ modes of these nonlinear molecules determine the fixed-orientation vibrational polarizability, reported as $\alpha_{\mathrm{vib}}/(4\pi\epsilon_0)$ in \AA$^3$. This quantity excludes orientational polarization of a freely rotating gas. The projection is not a geometry optimization: reference forces must first satisfy the equilibrium check. H$_2$O has three internal modes, with a maximum Cartesian--unified frequency difference of 0.449~cm$^{-1}$ and a relative vibrational-polarizability difference of 0.0606\%. For the nine CH$_4$ internal modes, these differences are below $5\times10^{-6}$~cm$^{-1}$ and 0.00188\%, respectively. The maximum raw APT differences are $8.19\times10^{-5}\,e$ for H$_2$O and $4.49\times10^{-6}\,e$ for CH$_4$. Numerical tests include a linear molecule with five rigid motions, coordinate-rotation covariance, isotope scaling, and rejection of unstable internal modes.

\subsection{One-dimensional reconstruction checks}
Both one-dimensional cases use a 100~Ry charge-density cutoff, a $1\times1\times12$ axial SCF mesh, a density convergence threshold of $10^{-8}$, and a symmetry tolerance of $10^{-5}$~\AA{}. The retained B and N orbitals have 10-bohr radii; Sb and S use 9-bohr orbitals. Pseudopotentials, orbital files, written displacement vectors, and PYATB input settings accompany each case. The structures are centered in the open transverse directions, with the periodic axis along $z$.

Against the matched Cartesian BEC and independent force calculations, the maximum raw BEC differences are $2.08\times10^{-4}\,e$ for BN(9,0) and $1.04\times10^{-3}\,e$ for Sb$_2$S$_3$. The relative raw-Hessian differences are $1.18\times10^{-5}$ and $4.91\times10^{-5}$, respectively. Mass-weighted eigenvector overlaps independently identify three translations and an axial rigid rotation in both routes. The remaining 104 BN(9,0) and 26 Sb$_2$S$_3$ modes are positive. Their maximum frequency differences are 0.514 and 0.0184~cm$^{-1}$. The BN difference occurs in the lowest pair near 48~cm$^{-1}$, illustrating the greater relative sensitivity of low-frequency eigenvalues to small force-constant changes. For Sb$_2$S$_3$, the larger all-mode difference of 0.769~cm$^{-1}$ belongs to the near-zero axial rotation (1.515 versus 2.284~cm$^{-1}$); both eigenvectors have rigid-motion overlap above 0.9997. These modes are classified by displacement character, not by selecting a frequency window to improve agreement.

The example-specific offline verifier reconstructs raw and projected tensors from archived force/dipole observations, checks the dynamical-matrix eigenvectors, recalculates both spectra, and verifies file hashes and solver-time ledgers. The Cartesian BEC and independent-force reconstructions are also reproduced from their own archived observations. These checks establish data consistency and reproducibility, not equivalence of different electronic-response approximations or validation of all Raman relative intensities. Finite-wavevector stability is outside these zone-center tests.


```
