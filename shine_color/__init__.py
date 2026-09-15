"""Python reimplementation of the repaired SHINE_color MATLAB reference.

The numerical kernel and narrow RGB/HSV/Lab color layer are implemented.
GNU Octave is the current executable reference. Kernel validation explicitly
documents backend-sensitive Fourier degeneracies; color validation uses
scikit-image HSV and a NumPy adapter for Octave Lab conventions. Mode dispatch,
iteration orchestration and file I/O are not implemented. See docs/VALIDATION.md
for the corpus-bound claims. MATLAB validation remains a future secondary target.

Each function lives in its own module, mirroring the MATLAB reference's
one-function-per-file layout; import from the specific submodule you
need (e.g. `from shine_color.rescale import rescale`) rather than from
the package root.
"""

__version__ = "0.1.0.dev0"
