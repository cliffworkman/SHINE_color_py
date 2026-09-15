"""Whole-image SHINE_color orchestration; no masks, optimization or filesystem I/O."""
from collections.abc import Sequence
from numbers import Integral
import numpy as np

from . import color, histogram, luminance, spatial_frequency, spectrum
from .numeric import to_uint8

_MODES = {
    1: ('lum',), 2: ('hist',), 3: ('sf',), 4: ('spec',),
    5: ('hist','sf'), 6: ('hist','spec'), 7: ('sf','hist'), 8: ('spec','hist'),
}


def _process_channel(images, mode, iterations, rescale_option, *, rng=None):
    """Keep every iteration/stage on uint8 SHINE working scale.

    rng is a private test hook. Production calls use the histogram primitive's
    fresh randomness. Spectral rescaling belongs to its primitive, not this loop.
    """
    current = list(images)
    for _ in range(iterations):
        for operation in _MODES[mode]:
            if operation == 'lum':
                current = luminance.lum_match(current)
            elif operation == 'hist':
                current = histogram.hist_match(current, rng=rng)
            elif operation == 'sf':
                current = spatial_frequency.sf_match(current, rescale_option)
            else:
                current = spectrum.spec_match(current, rescale_option)
    return current


def run(images, colorspace, mode, iterations=1, rescale_option=1):
    """Return a list of transformed, terminal RGB uint8 images.

    images: sequence of at least two nonempty same-shape (H,W,3) uint8 arrays.
    colorspace: 'RGB', 'HSV', or 'CIELab' (case-insensitive; 'Lab' alias).
    mode: 1 lum; 2 hist; 3 sf; 4 spec; 5 hist->sf; 6 hist->spec;
          7 sf->hist; 8 spec->hist. Mode is explicit, with no silent default.
    iterations: positive integer. Each pass consumes the preceding output.
    rescale_option: 0/1/2; used only by spectral stages (modes 3..8).

    Convert once, process only working channels, reconstruct once. Original
    H/S or a*/b* survives all iterations. Source arrays are not mutated.
    Histogram tie ordering is intentionally random, so pixel locations can vary.
    """
    if not isinstance(colorspace,str) or colorspace.lower() not in ('rgb','hsv','cielab','lab'):
        raise ValueError("colorspace must be RGB, HSV or CIELab")
    for name,value,allowed in [('mode',mode,range(1,9)),('rescale_option',rescale_option,range(3))]:
        if isinstance(value,bool) or not isinstance(value,Integral) or value not in allowed:
            raise ValueError(f'{name} is outside its supported integer range')
    if isinstance(iterations,bool) or not isinstance(iterations,Integral) or iterations<1:
        raise ValueError('iterations must be a positive integer')
    if not isinstance(images,Sequence) or isinstance(images,(str,bytes)):
        raise TypeError('images must be a sequence of RGB arrays')
    if len(images)<2:
        raise ValueError('at least two images are required')
    for image in images:
        if not isinstance(image,np.ndarray) or image.dtype!=np.uint8:
            raise TypeError('each RGB image must be a uint8 NumPy array')
        if image.ndim!=3 or image.shape[-1]!=3 or min(image.shape[:2])<1:
            raise ValueError('each image must have nonempty shape (H,W,3)')
        if image.shape!=images[0].shape:
            raise ValueError('all images must have the same dimensions')
    space=colorspace.lower()
    if space=='cielab': space='lab'
    parts=[getattr(color,'split_'+space)(image) for image in images]
    indices=(0,1,2) if space=='rgb' else ((2,) if space=='hsv' else (0,))
    transformed=[list(p) for p in parts]
    for channel in indices:
        output=_process_channel([p[channel] for p in parts],mode,iterations,rescale_option)
        for part,value in zip(transformed,output): part[channel]=value
    native=[getattr(color,'merge_'+space)(*p) for p in transformed]
    # RGB channels are already uint8; HSV/Lab inverse stays native and unclipped
    # until this one explicit public output boundary. Diagnostics must use the
    # working arrays above, never mix them with native L*/V or reconstructed RGB.
    return native if space=='rgb' else [to_uint8(image*255.0) for image in native]
