"""Compare unshifted computed spectra against original public sampled curves."""

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def draw_structure(ax, result):
    record = json.loads((result / 'response.json').read_text())['structure']
    cell = np.array(record['cell_angstrom'])
    positions = np.array(record['scaled_positions']) @ cell
    symbols = np.array(record['symbols'])
    positions = np.concatenate([positions + k * cell[2] for k in (-1, 0, 1)])
    symbols = np.tile(symbols, 3)
    positions -= positions.mean(axis=0)
    # Orthographic projection with an orthonormal viewing basis; no anisotropic scaling.
    u = np.array([.92, -.392, 0.])
    u /= np.linalg.norm(u)
    v = np.array([.0784, .184, .98])
    v -= np.dot(v, u) * u
    v /= np.linalg.norm(v)
    view = positions @ np.array([u, v]).T
    for i in range(len(positions)):
        for j in range(i):
            if symbols[i] != symbols[j] and 2.1 < np.linalg.norm(positions[i]-positions[j]) < 3.3:
                ax.plot(view[[i,j], 0], view[[i,j], 1], color='#999999', lw=1.2, zorder=1)
    for symbol, color, size in [('Sb', '#8b6ca8', 100), ('S', '#d9b42c', 65)]:
        pick = symbols == symbol
        ax.scatter(view[pick,0], view[pick,1], s=size, c=color,
                   edgecolors='#555555', linewidths=.4, label=symbol, zorder=2)
    ax.set_aspect('equal')
    ax.set_xlim(view[:,0].min()-1.5, view[:,0].max()+1.5)
    ax.set_ylim(view[:,1].min()-2.5, view[:,1].max()+2.2)
    ax.axis('off')
    ax.set_title(r'(a)  Sb$_2$S$_3$' + '\n     1D, Nanowire', loc='left', fontsize=11)
    ax.legend(loc='lower center', ncol=2, fontsize=9, handletextpad=.2, columnspacing=.5)


def plot(root, packaged=False, with_structure=False, reference_label='Ref. [1]'):
    case = root / 'results' if packaged else root / 'Sb2S3'
    reference = case / 'reference/B3LYP-D3/gamma-point' if packaged else root / 'reference/Sb2S3/B3LYP-D3/gamma-point'
    output = case / 'comparison'
    output.mkdir(exist_ok=True)
    files = [case / ('IR/ir_spectrum.dat' if packaged else 'ir/ir_spectrum.dat'),
             case / ('Raman/raman_spectrum.dat' if packaged else 'raman_spectrum/raman_spectrum.dat'),
             reference / 'sb2s3_fc_b3lyp-d3_freq.irspec.dat',
             reference / 'sb2s3_fc_b3lyp-d3_freq.ramspec.dat']
    arrays = [np.loadtxt(path) for path in files]
    if any(not np.all(np.isfinite(a)) for a in arrays):
        raise ValueError('Nonfinite spectrum')
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'pdf.fonttype': 42, 'svg.fonttype': 'none',
                         'axes.linewidth': .8, 'legend.frameon': False})
    fig, axes = plt.subplots(1, 3 if with_structure else 2,
                             figsize=(10.2, 3.4) if with_structure else (7.2, 3.2),
                             layout='constrained')
    if with_structure:
        draw_structure(axes[0], case)
        axes = axes[1:]
    for i, (ax, kind, color, own_column, ref_column) in enumerate(zip(
            axes, ['IR', 'Raman'], ['#c83e42', '#2466a8'], [4, 1], [2, 1])):
        own, ref = arrays[i], arrays[i + 2]
        for data, column, linecolor, label in [
                (ref, ref_column, '#aaaaaa', reference_label),
                (own, own_column, color, 'ZStar')]:
            if np.max(data[:, column]) <= 0:
                raise ValueError('Spectrum has no positive intensity')
            ax.plot(data[:, 0], data[:, column] / np.max(data[:, column]),
                    color=linecolor, lw=1.3, label=label)
        ax.set(xlim=(0, 390), ylim=(0, 1.25), xlabel=r'Wavenumber (cm$^{-1}$)',
               ylabel=f'Normalized {kind} intensity')
        ax.tick_params(direction='in', top=True, right=True)
        ax.set_yticks([0, .5, 1])
        ax.text(.025, .96, f'({chr(97 + i + int(with_structure))})', transform=ax.transAxes,
                va='top', fontsize=11, fontweight='normal')
        handles, labels = ax.get_legend_handles_labels()
        ax.legend(handles[::-1], labels[::-1], loc='upper right', ncol=2,
                  handlelength=1.4, columnspacing=.9, fontsize=9)
    for ext in ['png', 'pdf', 'svg']:
        suffix = '_with_structure' if with_structure else ''
        fig.savefig(output / f'Sb2S3_IR_Raman_comparison{suffix}.{ext}', dpi=300)
    plt.close(fig)
    metadata = dict(
        conclusion='A cross-functional comparison of isolated Sb2S3-chain IR and Raman spectra; agreement is assessed, not assumed.',
        reference_doi='10.17632/6tntvw37tr.1', reference_license='CC BY 4.0',
        reference_xc='B3LYP-D3(BJ)', calculation_xc='PBE-D3(BJ)',
        reference_curves='Original sampled IR column 3 and Raman column 2; not reconstructed from frequency markers.',
        reference_damping_cm1=8, zstar_lorentzian_fwhm_cm1=8,
        frequency_shift_cm1=0, intensity_scaling='Each curve divided by its own full-grid maximum.',
        displayed_range_cm1=[0, 390], source_points_preserved=True,
        caveat='Reference 31.5762 cm^-1 mode has ~98.3% axial-rotation overlap; retained in its original curve. Different XC and electronic-response approximations preclude claiming absolute-intensity validation.',
        sources=[dict(path=str(p.relative_to(root)), sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files])
    (output / 'comparison_metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('campaign_root', type=Path)
    parser.add_argument('--packaged', action='store_true', help='Input is a packaged case directory')
    parser.add_argument('--with-structure', action='store_true')
    parser.add_argument('--reference-label', default='Ref. [1]')
    args = parser.parse_args()
    plot(args.campaign_root, args.packaged, args.with_structure, args.reference_label)
