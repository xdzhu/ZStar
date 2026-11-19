"""Prepare a PYATB input for a Hamiltonian exported in ABACUS text format."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import math
import re
from tempfile import TemporaryDirectory

import numpy as np

from .structure_io import read_structure


MODELS = ("hamgnn", "deeph", "nextham")
_PARAMETERS = re.compile(r"(?ms)^[ \t]*INPUT_PARAMETERS[ \t]*\n\s*\{[^}]*\}")
_DIMENSION = re.compile(r"^Matrix Dimension(?:\s+(?:of|with)\s+\S+)?\s+(\d+)\s*$")


def _value(block, name, default=None):
    matches = re.findall(rf"(?m)^[ \t]*{name}[ \t]+([^\s#]+)", block)
    if not matches and default is not None:
        return default
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one {name} in PYATB INPUT_PARAMETERS")
    return matches[0]


def _resolve(parent, value):
    path = (parent / value).resolve(strict=True)
    if not path.is_file() or any(char.isspace() for char in str(path)):
        raise ValueError(f"PYATB requires an existing file at a path without spaces: {path}")
    return path


def _dimension(path):
    with path.open(encoding="utf-8") as stream:
        for _ in range(2):
            match = _DIMENSION.fullmatch(stream.readline().strip())
            if match:
                size = int(match[1])
                if size > 0:
                    return size
    raise ValueError(f"{path} does not start with an ABACUS text sparse-matrix header")


def _sha(path):
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_pyatb_hamiltonian(input_path, hamiltonian, structure, prediction_structure,
                              *, model, fermi_energy_ev, output_dir):
    """Keep S and r and replace H for the specified displaced geometry.

    The caller exports the prediction in the same numerical orbital basis
    and atom order as S and r. This function checks geometry and matrix sizes.
    """
    if model not in MODELS or not math.isfinite(fermi_energy_ev):
        raise ValueError("Provide a supported model name and a finite Fermi level in eV")
    cwd = Path.cwd()
    input_path = _resolve(cwd, input_path)
    hamiltonian = _resolve(cwd, hamiltonian)
    structure = _resolve(cwd, structure)
    prediction_structure = _resolve(cwd, prediction_structure)
    reference = read_structure(structure)
    prediction = read_structure(prediction_structure)
    if (reference.symbols != prediction.symbols
            or not np.allclose(reference.lattice_angstrom, prediction.lattice_angstrom,
                               atol=1e-6, rtol=0)):
        raise ValueError("Prediction atom order or lattice differs from reference")
    delta = prediction.positions_fractional - reference.positions_fractional
    delta -= np.rint(delta)
    if np.max(np.abs(delta @ reference.lattice_angstrom)) > 1e-6:
        raise ValueError("Prediction was made for different atomic positions")

    text = input_path.read_text(encoding="utf-8-sig")
    matches = list(_PARAMETERS.finditer(text))
    if len(matches) != 1:
        raise ValueError("Expected one PYATB INPUT_PARAMETERS block")
    parameters = matches[0]
    block = parameters[0]
    if (_value(block, "package").lower() != "abacus"
            or _value(block, "nspin") != "1"
            or _value(block, "binary", "0") != "0"
            or _value(block, "HR_unit") != "Ry"
            or _value(block, "fermi_energy_unit") != "eV"):
        raise ValueError("Use nonmagnetic ABACUS text matrices with H in Ry and Fermi energy in eV")
    overlap = _resolve(input_path.parent, _value(block, "SR_route"))
    position = _resolve(input_path.parent, _value(block, "rR_route"))
    size = _dimension(hamiltonian)
    if size != _dimension(overlap) or size != _dimension(position):
        raise ValueError("Hamiltonian, overlap and position matrices have different basis sizes")
    edits = {"HR_route": hamiltonian.as_posix(), "SR_route": overlap.as_posix(),
             "rR_route": position.as_posix(), "fermi_energy": f"{fermi_energy_ev:.16g}"}
    for key, value in edits.items():
        _value(block, key)
        block = re.sub(rf"(?m)^([ \t]*{key}[ \t]+)[^\n#]+",
                       lambda match: match[1] + value + " ", block)
    text = text[:parameters.start()] + block + text[parameters.end():]
    structure_entries = list(re.finditer(r"(?m)^([ \t]*stru_file[ \t]+)([^\s#]+)", text))
    if not structure_entries:
        raise ValueError("The template must contain a POLARIZATION structure")
    for entry in structure_entries:
        if _resolve(input_path.parent, entry[2]) != structure:
            raise ValueError("The requested structure does not match the PYATB template")
    text = re.sub(r"(?m)^([ \t]*stru_file[ \t]+)[^\s#]+",
                  lambda match: match[1] + structure.as_posix(), text)
    output = Path(output_dir).resolve()
    if output.exists():
        raise FileExistsError(f"Choose a new output directory: {output}")
    sources = {"template": input_path, "hamiltonian": hamiltonian,
               "overlap": overlap, "position": position, "structure": structure,
               "prediction_structure": prediction_structure}
    receipt = {"model": model, "fermi_energy_eV": fermi_energy_ev, "basis_dimension": size,
               "source_files": {name: {"path": str(path), "sha256": _sha(path)}
                                for name, path in sources.items()}}
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent) as scratch:
        prepared = Path(scratch) / "prepared"
        prepared.mkdir()
        (prepared/"Input").write_text(text, encoding="utf-8", newline="\n")
        (prepared/"hamiltonian_source.json").write_text(
            json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        prepared.rename(output)
    return output
