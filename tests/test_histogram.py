import numpy as np
import pytest

from shine_color.histogram import (
    average_histogram,
    hist_match,
    histogram_to_value_list,
    match_histogram,
)
from shine_color.numeric import imhist256


def test_average_histogram_basic():
    a = np.zeros((2, 2), dtype=np.uint8)      # 4 pixels at 0
    b = np.full((2, 2), 4, dtype=np.uint8)    # 4 pixels at 4
    hist = average_histogram([a, b])
    assert hist.shape == (256,)
    assert hist[0] == 2   # (4 + 0)/2
    assert hist[4] == 2   # (0 + 4)/2
    assert hist.sum() == 4  # matches per-image pixel count


def test_average_histogram_rounds_half_away_from_zero():
    # bin 0: image A contributes count 2, image B contributes count 3 ->
    # average 2.5. Away-from-zero rounding gives 3; Python's/NumPy's
    # round-half-to-even gives 2 (2 is the nearest even integer) -- a
    # genuinely distinguishing case.
    a = np.array([[0, 0]], dtype=np.uint8)       # bin 0 count = 2
    b = np.array([[0, 0, 0]], dtype=np.uint8)    # bin 0 count = 3
    hist = average_histogram([a, b])
    assert hist[0] == 3
    assert hist[0] != round(2.5)


def test_histogram_to_value_list_basic():
    hist = np.zeros(256, dtype=np.int64)
    hist[0] = 2
    hist[5] = 1
    hist[255] = 3
    values = histogram_to_value_list(hist)
    np.testing.assert_array_equal(values, [0, 0, 5, 255, 255, 255])


class TestMatchHistogram:
    def test_output_shape_and_dtype(self):
        image = np.arange(16, dtype=np.uint8).reshape(4, 4)
        target = np.sort(image.ravel().astype(np.float64))
        rng = np.random.default_rng(0)
        out = match_histogram(image, target, rng=rng)
        assert out.shape == image.shape
        assert out.dtype == np.float64  # unclamped, per match.m

    def test_reproduces_target_histogram_across_independent_seeds(self):
        image = np.tile(np.array([10, 10, 200, 200], dtype=np.uint8), (4, 1))
        target = histogram_to_value_list(average_histogram([image]))
        expected_hist = average_histogram([image])
        for seed in range(5):
            rng = np.random.default_rng(seed)
            out = match_histogram(image, target, rng=rng)
            out_uint8 = np.clip(np.round(out), 0, 255).astype(np.uint8)
            np.testing.assert_array_equal(imhist256(out_uint8), expected_hist)

    def test_tied_pixels_get_different_spatial_assignment_across_seeds(self):
        # A region of tied (identical) pixel values should be assigned
        # DIFFERENT output positions under different seeds, even though
        # the resulting histogram is identical every time -- this is the
        # randomized-tie-break behavior the reference deliberately
        # relies on, not a bug to be made deterministic.
        image = np.full((4, 4), 128, dtype=np.uint8)
        target = np.concatenate([np.zeros(8), np.full(8, 255)]).astype(np.float64)

        out_seed1 = match_histogram(image, target, rng=np.random.default_rng(1))
        out_seed2 = match_histogram(image, target, rng=np.random.default_rng(2))

        assert not np.array_equal(out_seed1, out_seed2)

        h1 = imhist256(np.clip(np.round(out_seed1), 0, 255).astype(np.uint8))
        h2 = imhist256(np.clip(np.round(out_seed2), 0, 255).astype(np.uint8))
        expected = np.zeros(256, dtype=np.int64)
        expected[0] = 8
        expected[255] = 8
        np.testing.assert_array_equal(h1, expected)
        np.testing.assert_array_equal(h2, expected)

    def test_single_pixel_first_target_octave_validated(self):
        # Octave selects the first target when target length is greater than 1.
        # The length-1 accepted divergence is tested in tests/reference.
        image = np.array([[42.0]])
        target = np.array([10.0, 200.0])
        out = match_histogram(image, target, rng=np.random.default_rng(0))
        assert out.shape == (1, 1)
        np.testing.assert_array_equal(out, [[10.0]])

    def test_default_rng_is_fresh_and_unseeded_each_call(self):
        # Two calls with rng=None (the runtime default) on a tied region
        # should be free to differ -- confirms the default path does NOT
        # silently fall back to a fixed seed.
        image = np.full((6, 6), 100, dtype=np.uint8)
        target = np.linspace(0, 255, 36).astype(np.float64)
        results = [match_histogram(image, target) for _ in range(5)]
        assert not all(np.array_equal(results[0], r) for r in results[1:])


class TestHistMatch:
    def test_each_output_matches_set_wide_target_histogram(self):
        a = np.array([[0, 0, 255, 255]], dtype=np.uint8)
        b = np.array([[100, 100, 150, 150]], dtype=np.uint8)
        target_hist = average_histogram([a, b])

        out = hist_match([a, b], rng=np.random.default_rng(42))
        for image in out:
            assert image.dtype == np.uint8
            np.testing.assert_array_equal(imhist256(image), target_hist)

    def test_rejects_mismatched_shapes(self):
        a = np.zeros((2, 2), dtype=np.uint8)
        b = np.zeros((3, 3), dtype=np.uint8)
        with pytest.raises(ValueError):
            hist_match([a, b])
