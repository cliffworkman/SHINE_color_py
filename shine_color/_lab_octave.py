"""D65 Lab compatibility with Octave 11.1.0 / image 2.18.2.

Derived from docs/OCTAVE_LAB_SPEC.md and measured reference conventions.
The rounded inverse matrix is intentional; native RGB is never clipped.
This is not a promise of MATLAB numerical parity.
"""
import numpy as np

_WHITE = np.array([0.95047, 1.0, 1.08883])
_RGB_XYZ = np.array([[0.412453, 0.357580, 0.180423],
                     [0.212671, 0.715160, 0.072169],
                     [0.019334, 0.119193, 0.950227]])
_XYZ_RGB = np.array([[3.240479, -1.537150, -0.498535],
                     [-0.969256, 1.875992, 0.041556],
                     [0.055648, -0.204043, 1.057311]])
_EPSILON = (6.0 / 29.0) ** 3
_SLOPE = (29.0 / 3.0) ** 3 / 116.0
_OFFSET = 16.0 / 116.0


def _triples(values):
    array = np.asarray(values)
    if array.ndim < 1 or array.shape[-1] != 3:
        raise ValueError('Expected a final axis of three color components')
    return array


def _rgb_uint8(rgb):
    array = _triples(rgb)
    if array.dtype != np.uint8:
        raise TypeError('RGB input must be uint8 in 0..255')
    return array


def rgb_to_lab_octave(rgb):
    """Convert uint8 sRGB (..., 3) to native float64 D65 L*, a*, b*."""
    encoded = _rgb_uint8(rgb).astype(np.float64) / 255.0
    linear = encoded / 12.92
    high = encoded > 0.04045
    linear[high] = ((encoded[high] + 0.055) / 1.055) ** 2.4
    relative_xyz = (linear @ _RGB_XYZ.T) / _WHITE
    auxiliary = _SLOPE * relative_xyz + _OFFSET
    high = relative_xyz > _EPSILON
    auxiliary[high] = relative_xyz[high] ** (1.0 / 3.0)
    x, y, z = np.moveaxis(auxiliary, -1, 0)
    return np.stack((116.0*y-16.0, 500.0*(x-y), 200.0*(y-z)), axis=-1)


def lab_to_rgb_octave(lab):
    """Convert native Lab (..., 3) to float64 sRGB, preserving out-of-gamut values.

    Terminal uint8 conversion, when desired, is numeric.to_uint8(rgb * 255).
    It is deliberately separate from this native conversion.
    """
    values = _triples(lab).astype(np.float64)
    lightness, a, b = np.moveaxis(values, -1, 0)
    y = (lightness + 16.0) / 116.0
    auxiliary = np.stack((y+a/500.0, y, y-b/200.0), axis=-1)
    cube = auxiliary ** 3
    relative_xyz = np.where(cube > _EPSILON, cube, (auxiliary-_OFFSET)/_SLOPE)
    linear = (relative_xyz * _WHITE) @ _XYZ_RGB.T
    encoded = 12.92 * linear
    high = linear > 0.0031308
    encoded[high] = 1.055 * linear[high] ** (1.0 / 2.4) - 0.055
    return encoded
