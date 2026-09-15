"""Float64 HSV arithmetic specified in docs/OCTAVE_HSV_SPEC.md.

Native RGB remains unclipped. Terminal quantization belongs to the caller.
"""
import numpy as np
from ._lab_octave import _rgb_uint8, _triples


def rgb_to_hsv_octave(rgb):
    """Convert uint8 RGB (..., 3) to native float64 H, S, V."""
    values = _rgb_uint8(rgb).astype(np.float64) / 255.0
    maximum = values.max(axis=-1)
    minimum = values.min(axis=-1)
    chromatic = maximum != minimum
    span = maximum - minimum
    hue = np.zeros_like(maximum)
    saturation = np.zeros_like(maximum)
    # argmax selects R, then G, then B on ties, as specified.
    sector = values.argmax(axis=-1)
    for channel, first, second, offset in ((0, 1, 2, 0.0),
                                           (1, 2, 0, 1.0/3.0),
                                           (2, 0, 1, 2.0/3.0)):
        selected = chromatic & (sector == channel)
        numerator = values[..., first][selected] - values[..., second][selected]
        hue[selected] = offset + ((1.0/6.0) * numerator) / span[selected]
    hue = np.where(hue < 0, hue + 1.0, hue)
    saturation[chromatic] = 1.0 - minimum[chromatic] / maximum[chromatic]
    return np.stack((hue, saturation, maximum), axis=-1)


def hsv_to_rgb_octave(hsv):
    """Convert native finite HSV (..., 3) to unclipped float64 RGB."""
    values = _triples(hsv).astype(np.float64)
    hue, saturation, value = np.moveaxis(values, -1, 0)
    shifted = np.remainder(hue[..., None] - np.array([2.0/3.0, 0.0, 1.0/3.0]), 1.0)
    weight = np.zeros_like(shifted)
    rising = shifted < 1.0/6.0
    plateau = (shifted >= 1.0/6.0) & (shifted < 0.5)
    falling = (shifted >= 0.5) & (shifted < 2.0/3.0)
    weight[rising] = 6.0 * shifted[rising]
    weight[plateau] = 1.0
    weight[falling] = 4.0 - 6.0 * shifted[falling]
    base = value * (1.0 - saturation)
    chroma = saturation * value
    return base[..., None] + chroma[..., None] * weight
