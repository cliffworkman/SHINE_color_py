"""SHINE_color's exact histogram specification: `avgHist`, `hist2list`,
`match`, and `histMatch` (non-optimized path only).

Randomness note: `match`'s tie-breaking jitter is genuinely
non-deterministic in the reference (MATLAB reseeds `rand` from the wall
clock on every call, specifically so that pixels sharing an intensity
value get an arbitrary relative order). This module reproduces that
*behavior* -- fresh, unseeded randomness by default on every call -- not
any specific MATLAB PRNG sequence. A `rng` parameter is accepted purely
for deterministic testing; the runtime default is never a fixed seed.
"""

from __future__ import annotations

import numpy as np

from .numeric import imhist256, matlab_round, to_uint8


def average_histogram(images):
    """Set-wide target histogram, matching `avgHist.m` (whole-image, no mask).

    Input: sequence of N same-shape uint8-valued arrays.
    Output: int64 array of length 256 -- the per-bin arithmetic mean
    count across the N images, rounded to the nearest integer (ties away
    from zero). Not weighted by anything other than N.
    """
    arrays = [np.asarray(im) for im in images]
    total = np.zeros(256, dtype=np.float64)
    for a in arrays:
        total += imhist256(a)
    return matlab_round(total / len(arrays)).astype(np.int64)


def histogram_to_value_list(hist):
    """Expand a 256-bin histogram into its sorted value list, matching `hist2list.m`.

    Input: length-256 count array. Output: 1-D ascending array containing
    each intensity level repeated by its count (level i appears
    hist[i] times).
    """
    hist = np.asarray(hist).astype(np.int64)
    return np.repeat(np.arange(256), hist)


def match_histogram(image, target_values, rng=None):
    """Exact histogram specification for one image, matching `match.m`.

    Input: `image` (any-shape real/uint8 array), `target_values` (a
    sorted ascending 1-D value list, e.g. from `histogram_to_value_list`;
    need not be the same length as `image.size`). `rng`: optional
    `numpy.random.Generator` for deterministic tests -- if omitted, a
    fresh, unseeded generator is created for this call (mirroring the
    reference's per-call clock-reseed, not any specific MATLAB
    sequence).

    Output: float64 array, same shape as `image`, UNCLAMPED (the
    reference's own `match.m` returns unclamped double; clamping is the
    caller's responsibility, since `histMatch`'s SSIM-optimization path
    -- not implemented in this phase -- needs the unclamped
    intermediate).

    Algorithm: every pixel is jittered by uniform noise on [0, 0.1)
    purely to break ties, ranked, and then replaced by the target value
    at the matching rank (the target list resampled to `image.size`
    entries via nearest-index selection at evenly spaced positions, not
    interpolation). This is a rank-order value replacement through the
    target's empirical CDF -- pixel identity across two independently
    randomized calls is NOT expected to match, even for identical
    inputs; only the resulting histogram is.
    """
    if rng is None:
        rng = np.random.default_rng()

    flat = np.asarray(image, dtype=np.float64).ravel()
    target_values = np.asarray(target_values, dtype=np.float64)
    n_pixels = flat.size
    n_target = target_values.size

    jitter = rng.uniform(0.0, 0.1, size=n_pixels)
    order = np.argsort(flat + jitter)

    # Rank positions follow the reference's evenly spaced index selection.
    # Octave 11.1.0 probe: one source and one target produces a NaN index
    # and match.m errors. We intentionally retain a well-defined sole-target
    # result as an accepted Python divergence. One source with >1 targets
    # selects the first target in both runtimes. See docs/VALIDATION.md and
    # tests/reference/fixtures/single_pixel.json. MATLAB remains untested.
    positions = np.linspace(1.0, float(n_target), n_pixels)
    indices = matlab_round(positions).astype(np.int64) - 1
    indices = np.clip(indices, 0, n_target - 1)
    resampled_target = target_values[indices]

    out = np.empty(n_pixels, dtype=np.float64)
    out[order] = resampled_target
    return out.reshape(np.asarray(image).shape)


def hist_match(images, rng=None):
    """Set-wide exact histogram matching, matching `histMatch.m` (non-optimized path).

    Input: sequence of N same-shape uint8-valued arrays. `rng`: optional
    shared `numpy.random.Generator` for deterministic tests.
    Output: list of N uint8 arrays, each independently matched to the
    SAME set-wide target histogram (`average_histogram` of the input
    set). SSIM-optimized matching (reference `optim=1`) is not
    implemented in this phase.
    """
    arrays = [np.asarray(im) for im in images]
    shape = arrays[0].shape
    if any(a.shape != shape for a in arrays):
        raise ValueError("hist_match requires all images to share one shape")

    target_hist = average_histogram(arrays)
    target_values = histogram_to_value_list(target_hist)

    return [to_uint8(match_histogram(a, target_values, rng=rng)) for a in arrays]
