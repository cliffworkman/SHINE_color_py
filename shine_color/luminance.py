"""SHINE_color's `lumMatch`: whole-image mean/contrast matching.

This phase implements only the reference's whole-set-average-target
behavior (MATLAB's no-mask, no-explicit-target call form). Masked and
explicit-target forms are deferred to the foreground/background phase.
"""

from __future__ import annotations

import numpy as np

from .numeric import sample_std, to_uint8


def lum_match(images):
    """Match every image's mean and SD to the set's own averaged mean/SD.

    Input: sequence of N same-shape real-valued (or uint8) arrays.
    Output: list of N uint8 arrays, each individually affine-transformed
    so its mean and SD equal the set-wide averaged targets M, S.

    M and S are the *unweighted arithmetic mean* of each image's own
    mean/SD (sample SD, ddof=1 -- NOT `numpy.std`'s population default),
    not a pixel-weighted average. An image whose own SD is exactly 0 (a
    constant image) is not divided by zero: its output is the constant
    image M, rather than propagating a NaN from a 0/0 division.
    """
    arrays = [np.asarray(im, dtype=np.float64) for im in images]
    means = np.array([a.mean() for a in arrays])
    sds = np.array([sample_std(a) for a in arrays])

    target_mean = means.mean()
    target_sd = sds.mean()

    out = []
    for a, m, sd in zip(arrays, means, sds):
        if sd != 0:
            transformed = (a - m) / sd * target_sd + target_mean
        else:
            transformed = np.full_like(a, target_mean)
        out.append(to_uint8(transformed))
    return out
