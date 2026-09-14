import numpy as np
import pytest

from shine_color.numeric import matlab_round
from shine_color.spatial_frequency import _coefficient_map, _decompose, _radial_bin_grid, sf_match


def _expected_grid(xs, ys):
    f_cols = -ys / 2 + np.arange(ys)
    f_rows = -xs / 2 + np.arange(xs)
    xx, yy = np.meshgrid(f_cols, f_rows)
    r = matlab_round(np.hypot(xx, yy))
    if xs % 2 == 1 or ys % 2 == 1:
        r = r - 1
    return r.astype(np.int64)


def _broadband_pattern(xs, ys, seed):
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=(xs, ys)).astype(np.uint8)


def _low_frequency_pattern(size=8):
    # Exact-integer spatial frequencies (1 cycle across the image in each
    # dimension): the DFT of such a signal has zero spectral leakage, so
    # ALL of its energy sits at low radius, strictly within sfMatch's
    # cutoff for any reasonable image size.
    i = np.arange(size).reshape(-1, 1)
    j = np.arange(size).reshape(1, -1)
    values = 128 + 40 * np.cos(2 * np.pi * i / size) + 30 * np.sin(2 * np.pi * j / size)
    return np.clip(np.round(values), 0, 255).astype(np.uint8)


def test_radial_bin_grid_even_dimensions():
    np.testing.assert_array_equal(_radial_bin_grid(4, 4), _expected_grid(4, 4))


def test_radial_bin_grid_odd_dimensions_apply_correction():
    np.testing.assert_array_equal(_radial_bin_grid(5, 5), _expected_grid(5, 5))


def test_radial_bin_grid_correction_is_coupled_not_per_axis():
    # xs even, ys odd -> the -1 correction still applies to the WHOLE
    # grid, since it is triggered by EITHER dimension being odd, not
    # applied independently per axis.
    np.testing.assert_array_equal(_radial_bin_grid(4, 5), _expected_grid(4, 5))


def test_correction_is_not_a_no_op():
    # Removing the odd-dimension correction would shift every bin index
    # by 1 relative to the (correct) reference grid for an odd size.
    r_with_correction = _radial_bin_grid(5, 5)
    f = -2.5 + np.arange(5)
    xx, yy = np.meshgrid(f, f)
    r_without_correction = matlab_round(np.hypot(xx, yy)).astype(np.int64)
    assert not np.array_equal(r_with_correction, r_without_correction)
    np.testing.assert_array_equal(r_with_correction, r_without_correction - 1)


def test_high_frequency_corner_is_hard_zeroed():
    image = _broadband_pattern(8, 8, seed=1)
    _, amplitude = _decompose(image)
    xs, ys = image.shape
    r = _radial_bin_grid(xs, ys)
    n_bins = int(r.max()) + 1
    cutoff = np.floor(max(xs, ys) / 2)

    cmat = _coefficient_map(amplitude, amplitude, r, n_bins, cutoff)  # self-target

    assert (r > cutoff).any()  # sanity: this size actually has bins beyond cutoff
    assert np.all(cmat[r > cutoff] == 0.0)


def test_coefficient_is_one_within_cutoff_when_self_matching():
    image = _broadband_pattern(8, 8, seed=1)
    _, amplitude = _decompose(image)
    xs, ys = image.shape
    r = _radial_bin_grid(xs, ys)
    n_bins = int(r.max()) + 1
    cutoff = np.floor(max(xs, ys) / 2)

    cmat = _coefficient_map(amplitude, amplitude, r, n_bins, cutoff)
    within = r <= cutoff
    nonzero_energy = within & (amplitude > 0)
    assert nonzero_energy.any()  # sanity: broadband image has energy within cutoff
    np.testing.assert_allclose(cmat[nonzero_energy], 1.0, atol=1e-10)


def test_self_matching_reconstructs_low_frequency_image_almost_exactly():
    # A low-frequency-only image has none of its real energy beyond
    # sfMatch's cutoff, so matching it to its own spectrum should
    # reconstruct it almost exactly (up to uint8 rounding) -- an
    # end-to-end sanity check that decompose -> coefficient -> recombine
    # -> reconstruct are wired together correctly.
    image = _low_frequency_pattern(8)
    out = sf_match([image], rescale_option=0)[0]
    diff = np.abs(out.astype(np.int16) - image.astype(np.int16))
    assert diff.max() <= 1


def test_rejects_mismatched_shapes():
    a = np.zeros((4, 4), dtype=np.uint8)
    b = np.zeros((5, 5), dtype=np.uint8)
    with pytest.raises(ValueError):
        sf_match([a, b])


def test_output_shape_and_dtype():
    image = _broadband_pattern(6, 6, seed=2)
    out = sf_match([image], rescale_option=0)[0]
    assert out.dtype == np.uint8
    assert out.shape == image.shape


def test_rescale_option1_with_single_image_stretches_to_full_range():
    # rescale(option=1) on a SINGLETON set always stretches that image's
    # own reconstructed min/max to exactly [0, 255], regardless of
    # sfMatch's cutoff behavior -- this is a property of `rescale`
    # applied to a one-image set, confirming sf_match actually invokes
    # it for rescale_option=1.
    image = _broadband_pattern(8, 8, seed=3)
    out = sf_match([image], rescale_option=1)[0]
    assert out.min() == 0
    assert out.max() == 255
