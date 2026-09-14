"""MATLAB-compatible numeric primitives shared by every SHINE_color operation.

MATLAB and NumPy disagree, by default, on several small but load-bearing
numeric conventions used throughout the SHINE_color reference: saturating
integer casts, tie-breaking on `round`, and the denominator used for sample
standard deviation. Every one of those disagreements is centralized here so
that no algorithm module has to reason about it locally, and so that any
place still using a bare NumPy default (`.astype`, `np.round`, `np.std`)
instead of one of these helpers can be treated as a bug in review.
"""

from __future__ import annotations

import numpy as np


def matlab_round(x):
    """Round half away from zero, matching MATLAB's `round()`.

    NumPy's `np.round`/`np.rint` round half to even. MATLAB's `round()`
    (and the rounding MATLAB's integer-type casts perform) rounds halfway
    values away from zero instead: `round(2.5) == 3`, `round(-2.5) == -3`.
    This difference is load-bearing in `avgHist` (bin-count averaging),
    `match` (target-index resampling), and `sfMatch` (radial-bin
    rounding).
    """
    x = np.asarray(x, dtype=np.float64)
    return np.sign(x) * np.floor(np.abs(x) + 0.5)


def to_uint8(x):
    """Saturating, round-half-away-from-zero cast to uint8, as MATLAB's `uint8()` performs it.

    Input: any real-valued array (float; may contain NaN/Inf; may be
    outside [0, 255]). Output: uint8 array, same shape.

    `ndarray.astype(np.uint8)` is NOT an acceptable substitute: it
    truncates toward zero and wraps modulo 256 rather than saturating,
    and does not special-case NaN. MATLAB's integer-type conversion
    instead clips to the type's range, rounds ties away from zero, maps
    NaN to 0, and saturates +/-Inf to the type's max/min. This helper
    reproduces exactly that.
    """
    x = np.asarray(x, dtype=np.float64)
    x = np.where(np.isnan(x), 0.0, x)
    x = np.clip(x, 0.0, 255.0)
    x = matlab_round(x)
    x = np.clip(x, 0.0, 255.0)
    return x.astype(np.uint8)


def sample_std(x):
    """Sample standard deviation (ddof=1), matching MATLAB's `std`/`std2`.

    `numpy.std`'s default (`ddof=0`) computes the *population* SD, which
    is systematically smaller than MATLAB's default sample SD. Every
    mean/SD use in `lumMatch` depends on the sample (n-1) convention.
    MATLAB's `std` additionally special-cases a single-element input to
    return 0 rather than 0/0 = NaN; this helper matches that too, since a
    foreground/background mask can legitimately reduce a region to one
    pixel in a later phase of this port.
    """
    x = np.asarray(x, dtype=np.float64).ravel()
    if x.size <= 1:
        return 0.0
    return float(np.std(x, ddof=1))


def imhist256(channel):
    """Exact 256-bin per-intensity-level histogram, matching MATLAB's `imhist` on uint8 input.

    Input: integer-valued array with values in [0, 255] (uint8 or
    uint8-castable). Output: int64 array of length 256, where bin i is
    the count of pixels exactly equal to intensity i.

    `np.histogram(channel, bins=256)` bins by *value range*, not by
    integer level, and would not reproduce `imhist`'s exact per-level
    counts. `np.bincount` is the correct translation: it counts exact
    integer occurrences, exactly as `imhist` does for 8-bit input.
    """
    values = np.asarray(channel).ravel()
    if values.size and (values.min() < 0 or values.max() > 255):
        raise ValueError("imhist256 expects values in [0, 255]")
    return np.bincount(values.astype(np.int64), minlength=256)[:256]


def accumarray_sum(bin_index, values, n_bins):
    """Grouped sum, matching MATLAB's `accumarray(bin_index+1, values)` usage in `sfMatch`.

    Input: `bin_index` (0-based integer bin labels, any shape), `values`
    (same shape, the quantities to sum per bin), `n_bins` (output
    length). Output: float64 array of length `n_bins`, where entry k is
    the sum of `values` at every position where `bin_index == k`.

    MATLAB's `accumarray` cannot accept a 0 subscript, so `sfMatch.m`
    uses `bin_index + 1` throughout purely to work around that. NumPy
    indexing has no such restriction, so that offset is intentionally
    NOT reproduced here -- `np.bincount` groups directly on the 0-based
    labels.
    """
    bin_index = np.asarray(bin_index).ravel()
    values = np.asarray(values, dtype=np.float64).ravel()
    return np.bincount(bin_index, weights=values, minlength=n_bins)[:n_bins]
