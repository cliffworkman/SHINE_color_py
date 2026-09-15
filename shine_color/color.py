"""Narrow RGB/HSV/Lab working-channel conversions for SHINE_color.

HSV and Lab target GNU Octave 11.1.0 / image 2.18.2.
HSV/Lab inverse functions return native float64 RGB. Call to_uint8(rgb*255)
only when terminal quantization is needed. There is no pipeline dispatch here.
"""
import numpy as np
from ._hsv_octave import rgb_to_hsv_octave, hsv_to_rgb_octave

from ._lab_octave import _rgb_uint8, _triples, rgb_to_lab_octave, lab_to_rgb_octave
from .numeric import to_uint8


def _working_uint8(channel):
    array = np.asarray(channel)
    if array.dtype != np.uint8:
        raise TypeError('Working channels must be uint8 in 0..255')
    return array


def v_to_working(value):
    """Native HSV V -> SHINE uint8, using the shared saturating cast."""
    return to_uint8(np.asarray(value, dtype=np.float64) * 255.0)


def working_to_v(channel):
    return _working_uint8(channel).astype(np.float64) / 255.0


def l_to_working(lightness):
    """Native CIELab L* -> SHINE uint8, using the shared saturating cast."""
    return to_uint8(np.asarray(lightness, dtype=np.float64) * 2.55)


def working_to_l(channel):
    return _working_uint8(channel).astype(np.float64) / 2.55


def rgb_to_hsv(rgb):
    return rgb_to_hsv_octave(rgb)


def hsv_to_rgb(hsv):
    return hsv_to_rgb_octave(hsv)


def split_rgb(rgb):
    """Return independent uint8 R, G, B working channels."""
    return tuple(channel.copy() for channel in np.moveaxis(_rgb_uint8(rgb), -1, 0))


def merge_rgb(red, green, blue):
    return np.stack([_working_uint8(c) for c in (red, green, blue)], axis=-1)


def split_hsv(rgb):
    """Return untouched native H, S and quantized uint8 working V."""
    native = rgb_to_hsv(rgb)
    return native[...,0].copy(), native[...,1].copy(), v_to_working(native[...,2])


def merge_hsv(hue, saturation, working_v):
    """Recombine untouched H/S with processed working V, returning native RGB."""
    return hsv_to_rgb(np.stack((hue, saturation, working_to_v(working_v)), axis=-1))


def split_lab(rgb):
    """Return uint8 working L and untouched native a*, b*."""
    native = rgb_to_lab_octave(rgb)
    return l_to_working(native[...,0]), native[...,1].copy(), native[...,2].copy()


def merge_lab(working_l, a, b):
    """Recombine processed working L with untouched a*/b*, returning unclipped RGB."""
    return lab_to_rgb_octave(np.stack((working_to_l(working_l), a, b), axis=-1))
