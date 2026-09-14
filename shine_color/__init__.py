"""Python reimplementation of the repaired SHINE_color MATLAB reference.

This package currently implements only the color-space-independent
numerical kernel: `rescale`, whole-image `luminance.lum_match`,
non-optimized `histogram.hist_match`, `spatial_frequency.sf_match`, and
`spectrum.spec_match`. Color-space conversion, mode dispatch, iteration
orchestration, and file I/O are deferred pending MATLAB reference
fixtures -- see the project planning document for the full behavioral
specification and phased scope.

Each function lives in its own module, mirroring the MATLAB reference's
one-function-per-file layout; import from the specific submodule you
need (e.g. `from shine_color.rescale import rescale`) rather than from
the package root.
"""

__version__ = "0.1.0.dev0"
