"""SHINE_color's `specMatch`: full (non-radially-averaged) Fourier
amplitude spectrum matching.

Structurally identical to `sfMatch` (see `spatial_frequency.py`) up
through the FFT/phase/magnitude decomposition, but with NO radial
binning: the target magnitude is substituted pixel-for-pixel in
frequency space, not just its rotational average -- a strictly
stronger/different operation than `sfMatch`.
"""

from __future__ import annotations

import numpy as np

from .numeric import to_uint8
from .rescale import rescale as rescale_set


def _decompose(image):
    """FFT-shift, then Cartesian-to-polar decomposition -- see `spatial_frequency._decompose`.

    Duplicated (not shared) deliberately: the MATLAB reference itself
    keeps independent, inline copies of this decomposition in
    `sfMatch.m` and `specMatch.m` rather than sharing a helper, and each
    of these two modules should stay auditable in isolation.
    """
    spectrum = np.fft.fftshift(np.fft.fft2(np.asarray(image, dtype=np.float64) / 255.0))
    phase = np.arctan2(spectrum.imag, spectrum.real)
    amplitude = np.hypot(spectrum.real, spectrum.imag)
    return phase, amplitude


def spec_match(images, rescale_option=1):
    """Match each image's full 2-D amplitude spectrum to the set's own average.

    Input: sequence of N same-shape real/uint8 arrays. `rescale_option`:
    0 = bypass `rescale.py`, cast `output * 255` directly (saturating);
    1 or 2 = keep raw reconstructed doubles and rescale the whole set at
    the end via `rescale.rescale`.
    Output: list of N uint8 arrays.

    Every image gets the exact same target magnitude at every frequency
    bin (the unweighted mean amplitude spectrum across the set; custom
    override is not supported in this phase), combined with its own
    original phase. No radial averaging and no frequency cutoff are
    applied (unlike `sfMatch`).
    """
    arrays = [np.asarray(im, dtype=np.float64) for im in images]
    shape = arrays[0].shape
    if any(a.shape != shape for a in arrays):
        raise ValueError("spec_match requires all images to share one shape")

    phases, amplitudes = zip(*(_decompose(a) for a in arrays))
    target_amplitude = np.mean(np.stack(amplitudes, axis=0), axis=0)

    reconstructed = []
    for phase in phases:
        spectrum = target_amplitude * (np.cos(phase) + 1j * np.sin(phase))
        out = np.real(np.fft.ifft2(np.fft.ifftshift(spectrum)))
        reconstructed.append(out)

    if rescale_option == 0:
        return [to_uint8(out * 255.0) for out in reconstructed]
    return rescale_set(reconstructed, rescale_option)
