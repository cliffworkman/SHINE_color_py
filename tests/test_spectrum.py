import numpy as np
import pytest

from shine_color.spectrum import spec_match


def _broadband_pattern(xs, ys, seed):
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=(xs, ys)).astype(np.uint8)


def test_self_matching_reconstructs_the_same_image():
    # With no radial averaging and no cutoff, matching a single image to
    # its own (identical) amplitude spectrum, keeping its own phase,
    # should reconstruct the same image up to floating-point/rounding
    # noise -- unlike sfMatch, this holds for ANY image, not just a
    # low-frequency-only one, since there is no cutoff to remove content.
    image = _broadband_pattern(8, 8, seed=0)
    out = spec_match([image], rescale_option=0)[0]
    diff = np.abs(out.astype(np.int16) - image.astype(np.int16))
    assert diff.max() <= 1


def test_rejects_mismatched_shapes():
    a = np.zeros((4, 4), dtype=np.uint8)
    b = np.zeros((5, 5), dtype=np.uint8)
    with pytest.raises(ValueError):
        spec_match([a, b])


def test_rescale_option1_with_single_image_stretches_to_full_range():
    image = _broadband_pattern(8, 8, seed=1)
    out = spec_match([image], rescale_option=1)[0]
    assert out.min() == 0
    assert out.max() == 255


def test_output_shape_and_dtype():
    image = _broadband_pattern(6, 6, seed=2)
    out = spec_match([image], rescale_option=0)[0]
    assert out.dtype == np.uint8
    assert out.shape == image.shape
