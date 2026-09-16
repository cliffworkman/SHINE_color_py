"""Python reimplementation of the repaired SHINE_color MATLAB reference.

The numerical kernel and narrow RGB/HSV/Lab color layer are implemented.
GNU Octave is the current executable reference. Kernel validation explicitly
documents backend-sensitive Fourier degeneracies; color validation uses
NumPy adapters for Octave HSV and Lab conventions. Whole-image mode dispatch
and iteration orchestration in pipeline.py meet the Gate 4 corpus contract,
including positive tests for dynamically generated spectral degeneracy.
io.py and batch.py wrap the core with PNG/JPEG loading, exact PNG output and
group-level provenance. See docs/VALIDATION.md for the corpus-bound claims.
MATLAB validation remains a future secondary target.

Each function lives in its own module, mirroring the MATLAB reference's
one-function-per-file layout; import from the specific submodule you
need (e.g. `from shine_color.rescale import rescale`) rather than from
the package root.
"""

__version__ = "0.1.0.dev0"
