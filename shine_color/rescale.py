"""SHINE_color's own `rescale.m`: set-wide affine rescaling to [0, 255].

Distinct from MATLAB's built-in numeric `rescale()` (R2017b+, single-array,
different semantics) and from any NumPy/skimage rescale/normalize
function -- this module exists specifically because those alternatives do
not reproduce SHINE_color's two set-wide rescaling options.
"""

from __future__ import annotations

import numpy as np

from .numeric import to_uint8


def rescale(images, option):
    """Affine-rescale a set of images to [0, 255], per `rescale.m`.

    Input: a sequence of same-shape real-valued arrays (any scale -- the
    extrema are read from whatever values are actually passed in).
    Output: list of uint8 arrays, same shapes.

    option 1: every image is mapped by (image - D) / (B - D) * 255,
    where B/D are the single brightest/darkest pixel value across the
    *entire* set (global extrema).

    option 2: same formula, but using the arithmetic mean of each
    image's own max/min (B_bar/D_bar) instead of the global extrema. An
    individual image's own values can legitimately fall outside
    [0, 255] before the terminal saturating cast under this option --
    that overshoot is reference behavior, not a bug, and is not
    pre-clipped.

    No other option is accepted (mirrors `rescale.m`'s own
    `error('Invalid rescaling option.')`). The "no rescale" behavior
    (SHINE_color's `rescaling == 0`) is not a mode of this function --
    per the reference, callers bypass `rescale.m` entirely for that
    case.
    """
    if option not in (1, 2):
        raise ValueError(f"Invalid rescaling option: {option!r} (must be 1 or 2)")

    arrays = [np.asarray(im, dtype=np.float64) for im in images]
    maxima = np.array([a.max() for a in arrays])
    minima = np.array([a.min() for a in arrays])

    if option == 1:
        bright = maxima.max()
        dark = minima.min()
    else:
        bright = maxima.mean()
        dark = minima.mean()

    span = bright - dark
    out = []
    for a in arrays:
        with np.errstate(divide="ignore", invalid="ignore"):
            rescaled = (a - dark) / span * 255.0
        out.append(to_uint8(rescaled))
    return out
