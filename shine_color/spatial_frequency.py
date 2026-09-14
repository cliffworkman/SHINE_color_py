"""SHINE_color's `sfMatch`: rotationally-averaged Fourier amplitude
spectrum matching.

Operates purely on the SHINE working representation (real-valued arrays
already in the toolbox's internal 0-255-ish scale) -- no color-space
conversion happens here or anywhere in this phase.
"""

from __future__ import annotations

import numpy as np

from .numeric import accumarray_sum, matlab_round, to_uint8
from .rescale import rescale as rescale_set


def _radial_bin_grid(xs, ys):
    """Integer radial-distance bin index per pixel, matching `sfMatch.m`'s grid.

    Input: image shape (xs rows, ys columns).
    Output: int64 array of shape (xs, ys); entry [i, j] is the 0-based
    radial bin of that frequency-domain pixel after `fftshift`
    centering.

    The MATLAB reference applies a `-1` correction to the rounded radius
    whenever EITHER dimension is odd (not per-axis, coupled across
    both), to stay aligned with `fftshift`'s own odd/even centering
    convention. This is intentionally preserved exactly, not
    simplified.
    """
    f_cols = -ys / 2 + np.arange(ys)
    f_rows = -xs / 2 + np.arange(xs)
    xx, yy = np.meshgrid(f_cols, f_rows)
    r = matlab_round(np.hypot(xx, yy))
    if xs % 2 == 1 or ys % 2 == 1:
        r = r - 1
    return r.astype(np.int64)


def _decompose(image):
    """FFT-shift, then Cartesian-to-polar decomposition, matching `sfMatch.m`/`specMatch.m`.

    Returns (phase, amplitude), each shaped like `image`. Argument order
    is load-bearing: the reference computes
    `cart2pol(real(fft), imag(fft))`, i.e. phase = atan2(imag, real) and
    amplitude = hypot(real, imag) -- not the reverse.
    """
    spectrum = np.fft.fftshift(np.fft.fft2(np.asarray(image, dtype=np.float64) / 255.0))
    phase = np.arctan2(spectrum.imag, spectrum.real)
    amplitude = np.hypot(spectrum.real, spectrum.imag)
    return phase, amplitude


def _coefficient_map(amplitude, target_amplitude, r, n_bins, cutoff):
    """Per-pixel magnitude multiplier: per-radial-bin target/source energy
    ratio, hard-zeroed beyond `cutoff`.

    `en_old`/`en_new` are per-bin SUMS of amplitude (not means); because
    both are grouped by the same bin membership, their ratio is
    equivalent to a per-bin mean ratio without ever needing to count bin
    populations explicitly. Any bin beyond `cutoff` gets a multiplier of
    exactly 0 -- a hard cutoff, not a taper.
    """
    en_old = accumarray_sum(r, amplitude, n_bins)
    en_new = accumarray_sum(r, target_amplitude, n_bins)
    with np.errstate(divide="ignore", invalid="ignore"):
        coefficient = en_new / en_old
    cmat = coefficient[r]
    return np.where(r > cutoff, 0.0, cmat)


def sf_match(images, rescale_option=1):
    """Match each image's rotationally-averaged amplitude spectrum to the set's own average.

    Input: sequence of N same-shape real/uint8 arrays. `rescale_option`:
    0 = bypass `rescale.py` entirely, cast `output * 255` directly
    (saturating); 1 or 2 = keep the raw reconstructed doubles and
    rescale the whole set at the end via `rescale.rescale`.
    Output: list of N uint8 arrays.

    Each image's own phase is always preserved; only magnitude is
    replaced. The target magnitude (custom target override is not
    supported in this phase) is the unweighted mean amplitude spectrum
    across the set. Per radial bin, this image's magnitude is scaled by
    the target/source bin-energy ratio; any pixel beyond radius
    floor(max(xs, ys) / 2) is hard-zeroed, not tapered -- this is a
    real, intentional cutoff in the reference, not a Nyquist no-op.
    """
    arrays = [np.asarray(im, dtype=np.float64) for im in images]
    shape = arrays[0].shape
    if any(a.shape != shape for a in arrays):
        raise ValueError("sf_match requires all images to share one shape")
    xs, ys = shape

    phases, amplitudes = zip(*(_decompose(a) for a in arrays))
    target_amplitude = np.mean(np.stack(amplitudes, axis=0), axis=0)

    r = _radial_bin_grid(xs, ys)
    n_bins = int(r.max()) + 1
    cutoff = np.floor(max(xs, ys) / 2)

    reconstructed = []
    for phase, amplitude in zip(phases, amplitudes):
        cmat = _coefficient_map(amplitude, target_amplitude, r, n_bins, cutoff)
        new_amplitude = amplitude * cmat
        spectrum = new_amplitude * (np.cos(phase) + 1j * np.sin(phase))
        out = np.real(np.fft.ifft2(np.fft.ifftshift(spectrum)))
        reconstructed.append(out)

    if rescale_option == 0:
        return [to_uint8(out * 255.0) for out in reconstructed]
    return rescale_set(reconstructed, rescale_option)
