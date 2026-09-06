"""Evidence-limited comparison: original curves, digitized curves, or frequencies."""

import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'examples/IR_Raman_Spectra'
OUT = BASE / 'one_dimensional_comparison'


def digitize_bn9():
    source = ROOT / '.codex-tmp/one-dimensional-20260905/reference/BN/Wirtz2005.pdf'
    pixels = np.asarray(PdfReader(source).pages[2].images[0].image.convert('L'))
    if pixels.shape != (876, 900):
        raise ValueError('Reference image geometry changed; recalibrate digitization')
    # Fig. 3, first row, positive (ab initio) branch only. Upper masks exclude
    # printed labels; the negative bond-polarizability curve is never sampled.
    xs = np.arange(74, 895)
    ys = []
    for x in xs:
        top = 87
        for left, right, upper in [(84, 101, 74), (199, 210, 77),
                                   (458, 471, 79), (730, 746, 5)]:
            if left <= x <= right:
                top = upper
        ink = np.flatnonzero(pixels[top:94, x] < 128)
        ys.append(top + ink[0] if ink.size else 92)
    intensity = np.maximum(0, 92 - np.array(ys, dtype=float))
    # Label leader lines approach these intervals; omit them, do not interpolate.
    ambiguous = ((xs >= 210) & (xs <= 222)) | ((xs >= 454) & (xs <= 457))
    intensity[ambiguous] = np.nan
    data = np.column_stack(((xs - 69) * 1600 / (850 - 69),
                            intensity / np.nanmax(intensity)))
    np.savetxt(OUT / 'BN9_Raman_digitized.csv', data, delimiter=',',
               header='frequency_cm-1,normalized_intensity', comments='')
    # Retain an audit view of the actual tracing over the embedded source image.
    fig, ax = plt.subplots(figsize=(10, 3))
    ax.imshow(pixels, cmap='gray', vmin=0, vmax=255)
    yy = np.array(ys, dtype=float)
    yy[ambiguous] = np.nan
    ax.plot(xs, yy, color='#c83e42', lw=.65)
    ax.set(xlim=(60, 900), ylim=(190, 0), xlabel='Source image pixel x',
           ylabel='Source image pixel y')
    fig.tight_layout()
    fig.savefig(OUT / 'BN9_digitization_audit.png', dpi=180)
    plt.close(fig)
    return data, dict(doi='10.1103/PhysRevB.71.241402', figure='3, BN(9,0), positive branch',
                     source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                     calibration=dict(x0=69, x1600=850, y0=92),
                     masking='Manual source-image background masks exclude labels; peak windows verified against source, not against ZStar.',
                     uncertainty='Approximately 2-4 cm^-1 horizontally; weak intensities pixel-limited. Label-contaminated intervals omitted.',
                     xc='LDA', processing='Pixel trace, independent peak normalization, no shifts or smoothing')


def main():
    OUT.mkdir(exist_ok=True)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
                         'pdf.fonttype': 42, 'svg.fonttype': 'none',
                         'axes.linewidth': .85, 'legend.frameon': False})
    bn9, digitization = digitize_bn9()
    specs = [('Nanotube_BN_6_0', 'BN(6,0) nanotube', 'PBE'),
             ('Nanotube_BN_9_0', 'BN(9,0) nanotube', 'PBE'),
             ('Nanowire_Sb2S3', r'Sb$_2$S$_3$ chain', 'PBE-D3(BJ)')]
    fig, axes = plt.subplots(3, 2, figsize=(10, 9.2))
    fig.subplots_adjust(left=.095, right=.97, bottom=.085, top=.96,
                        hspace=.49, wspace=.24)
    sources = []
    for row, (folder, title, xc) in enumerate(specs):
        case = BASE / folder / 'results'
        for col, (kind, color, filename, column) in enumerate([
                ('IR', '#c83e42', 'IR/ir_spectrum.dat', 4),
                ('Raman', '#2466a8', 'Raman/raman_spectrum.dat', 1)]):
            ax = axes[row, col]
            path = case / filename
            a = np.loadtxt(path)
            if not np.all(np.isfinite(a)) or a[:, column].max() <= 0:
                raise ValueError(f'Invalid spectrum: {path}')
            sources.append(dict(path=str(path.relative_to(ROOT)),
                                sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
            ax.plot(a[:, 0], a[:, column] / a[:, column].max(),
                    color=color, lw=1.4, label='ZStar', zorder=3)
            note = 'No verified same-chirality reference curve'
            if row == 0 and col == 0:
                with (case / 'comparison/Erba2013_IR_frequencies.csv').open() as f:
                    frequencies = [float(r['reference_B3LYP_cm1']) for r in csv.DictReader(f)]
                ax.vlines(frequencies, 0, 1.01, color='#b2b2b2', ls=':', lw=1,
                          label='Ref. [1]: frequencies', zorder=1)
                note = 'Reference: B3LYP; frequency comparison only'
            elif row == 1 and col == 1:
                ax.plot(bn9[:, 0], bn9[:, 1], color='#a6a6a6', lw=1.4,
                        label='Ref. [2]', zorder=2)
                note = 'Reference: LDA; digitized ab initio curve'
            elif row == 2:
                suffix, refcol = ('irspec', 2) if col == 0 else ('ramspec', 1)
                rp = case / f'reference/B3LYP-D3/gamma-point/sb2s3_fc_b3lyp-d3_freq.{suffix}.dat'
                b = np.loadtxt(rp)
                ax.plot(b[:, 0], b[:, refcol] / b[:, refcol].max(),
                        color='#a6a6a6', lw=1.4, label='Ref. [3]', zorder=2)
                sources.append(dict(path=str(rp.relative_to(ROOT)),
                                    sha256=hashlib.sha256(rp.read_bytes()).hexdigest()))
                note = 'Reference: B3LYP-D3(BJ); original sampled curve'
            ax.set(xlim=(0, 1600 if row < 2 else 400), ylim=(0, 1.30),
                   xlabel=r'Wavenumber (cm$^{-1}$)', ylabel=f'Normalized {kind} intensity')
            ax.set_yticks([0, .5, 1])
            ax.tick_params(direction='in', top=True, right=True)
            ax.set_title(f'({chr(97 + row * 2 + col)})  {title} | {kind}',
                         loc='left', fontsize=12, pad=9, fontweight='normal')
            ax.legend(loc='upper right', ncol=2, fontsize=9.5,
                      handlelength=1.5, columnspacing=1)
            ax.text(0, -.31, note, transform=ax.transAxes, fontsize=9, color='#555555')
    for ext in ['png', 'pdf', 'svg']:
        fig.savefig(OUT / f'One_dimensional_IR_Raman_comparison.{ext}', dpi=240)
    plt.close(fig)
    metadata = dict(
        purpose='Inspect agreement and discrepancies, not assume validation.',
        frequency_shifts_cm1=0, normalization='Each full-grid curve independently peak-normalized.',
        zstar_fwhm_cm1=8, zstar_raman_temperature_K=298, zstar_raman_laser_nm=532,
        reference_1='Erba et al., 10.1063/1.4788831, Table I; frequencies only.',
        reference_2=digitization,
        reference_3='Ulian, 10.17632/6tntvw37tr.1, CC BY 4.0, original sampled curves.',
        missing=['BN(6,0) Raman reference curve', 'BN(9,0) IR reference curve'],
        caveats=['Different XC and response treatments; no absolute-intensity validation.',
                 'Sb2S3 reference retains its 31.5762 cm^-1 rotation-like mode.',
                 'BN9 digitized weak intensities are pixel limited; see audit image.',
                 'Reference indices are local to this comparison, not manuscript numbers.'],
        sources=sources)
    (OUT / 'comparison_metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(OUT)


if __name__ == '__main__':
    main()
