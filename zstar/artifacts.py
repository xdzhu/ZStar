"""Public result names and read-only compatibility with earlier archives."""

from pathlib import Path
import hashlib


LEGACY_NAMES = {
    "BORN-for-phonopy.out": "BORN",
    "Z-BORN-reduced-neutral.out": "BEC.rep.dat",
    "Z-BORN-reduced.out": "BEC.rep.raw.dat",
    "Z-BORN-all.out": "BEC.raw.dat",
    "Z-BORN-symm.out": "BEC.dat",
    "bec.rep.dat": "BEC.rep.dat",
    "bec.rep.raw.dat": "BEC.rep.raw.dat",
    "bec.raw.dat": "BEC.raw.dat",
    "bec.dat": "BEC.dat",
    "zstar_response.json": "response.json",
    "shared_response_result.json": "response_fit.json",
    "shared_forces_result.json": "force_fit.json",
    "molecular_apt.json": "apt.json",
    "molecular_apt_symmetry_report.json": "apt_symmetry.json",
    "molecular_apt_symmetry_report.txt": "apt_symmetry.txt",
    "born_symmetry_report.json": "BEC_symmetry.json",
    "born_symmetry_report.txt": "BEC_symmetry.txt",
    "bec_symmetry.json": "BEC_symmetry.json",
    "bec_symmetry.txt": "BEC_symmetry.txt",
}


def resolve_artifact(path: str | Path, *, explicit: bool = True) -> Path:
    """Resolve a known result basename without copying or editing old files.

    An existing explicitly supplied path always wins. For a missing canonical
    default, try all known spellings. Automatic discovery (explicit=False)
    rejects conflicting aliases. Unrecognized user filenames are not replaced.
    """
    path = Path(path)
    if explicit and path.exists():
        return path
    canonical = LEGACY_NAMES.get(path.name, path.name)
    candidates = [canonical, *(old for old, new in LEGACY_NAMES.items() if new == canonical)]
    found = []
    for name in candidates:
        candidate = path.with_name(name)
        if candidate.is_file():
            if not any(candidate.samefile(other) for other in found):
                found.append(candidate)
    if len(found) > 1:
        hashes = {hashlib.sha256(item.read_bytes()).digest() for item in found}
        if len(hashes) > 1:
            names = ', '.join(str(item) for item in found)
            raise ValueError(
                f"Conflicting result aliases for {canonical}: {names}. "
                "Select an explicit input path or move stale results out of this workspace."
            )
    if found:
        return found[0]
    return path
