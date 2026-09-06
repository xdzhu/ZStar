"""Lossless static tensor export for a bounded Raman benchmark; kernels unchanged."""
from pathlib import Path
import sys
import numpy as np


def main():
    import pyatb
    initialize = getattr(pyatb, 'initialize_runtime', None)
    if initialize is not None:
        initialize()
    from pyatb.berry.optical_conductivity import Optical_Conductivity
    from pyatb.main import main as run
    original = Optical_Conductivity.print_data

    def precise(self):
        original(self)
        if not hasattr(self, 'static_epsilon'):
            raise RuntimeError('A direct-static response is required for this benchmark')
        values = np.asarray(self.static_epsilon, dtype=float)
        if values.size != 9 or not np.all(np.isfinite(values)):
            raise ValueError('Invalid static dielectric tensor')
        target = Path(self.output_path) / 'static_dielectric_function.dat'
        target.with_name('static_dielectric_function.rounded.dat').write_bytes(target.read_bytes())
        np.savetxt(target, values.reshape(1, 9), fmt='%.16e',
                   header='xx xy xz yx yy yz zx zy zz')

    Optical_Conductivity.print_data = precise
    try:
        return run()
    finally:
        Optical_Conductivity.print_data = original


if __name__ == '__main__':
    sys.exit(main())
