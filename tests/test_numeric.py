import numpy as np
import pytest

from shine_color.numeric import accumarray_sum, imhist256, matlab_round, sample_std, to_uint8


class TestMatlabRound:
    def test_positive_half_rounds_up(self):
        assert matlab_round(np.array([2.5]))[0] == 3.0

    def test_negative_half_rounds_away_from_zero(self):
        assert matlab_round(np.array([-2.5]))[0] == -3.0

    def test_ordinary_values(self):
        result = matlab_round(np.array([1.4, 1.6, -1.4, -1.6]))
        np.testing.assert_array_equal(result, [1.0, 2.0, -1.0, -2.0])

    def test_disagrees_with_numpy_banker_rounding_at_even_half(self):
        # np.round(2.5) == 2.0 (round-half-to-even); MATLAB's round(2.5) == 3.0
        assert matlab_round(np.array([2.5]))[0] != np.round(2.5)


class TestToUint8:
    def test_ordinary_value(self):
        assert to_uint8(np.array([100.0]))[0] == 100

    def test_saturates_above_255(self):
        assert to_uint8(np.array([300.0]))[0] == 255

    def test_saturates_below_zero(self):
        assert to_uint8(np.array([-10.0]))[0] == 0

    def test_rounds_half_away_from_zero(self):
        assert to_uint8(np.array([2.5]))[0] == 3

    def test_nan_maps_to_zero(self):
        assert to_uint8(np.array([np.nan]))[0] == 0

    def test_positive_infinity_saturates_to_255(self):
        assert to_uint8(np.array([np.inf]))[0] == 255

    def test_negative_infinity_saturates_to_zero(self):
        assert to_uint8(np.array([-np.inf]))[0] == 0

    def test_dtype_is_uint8(self):
        assert to_uint8(np.array([1.0])).dtype == np.uint8

    def test_does_not_wrap_like_naive_astype(self):
        # np.array([300.0]).astype(np.uint8) wraps to 44; MATLAB (and
        # this helper) saturates to 255 instead.
        naive = np.array([300.0]).astype(np.uint8)[0]
        assert to_uint8(np.array([300.0]))[0] == 255
        assert naive != 255


class TestSampleStd:
    def test_matches_ddof1_not_population_sd(self):
        x = np.array([1.0, 2.0, 3.0, 4.0])
        assert sample_std(x) == pytest.approx(np.std(x, ddof=1))
        assert sample_std(x) != pytest.approx(np.std(x, ddof=0))

    def test_single_element_returns_zero_not_nan(self):
        assert sample_std(np.array([5.0])) == 0.0

    def test_empty_returns_zero(self):
        assert sample_std(np.array([])) == 0.0

    def test_constant_array_returns_zero(self):
        assert sample_std(np.full((4, 4), 7.0)) == 0.0


class TestImhist256:
    def test_basic_counts(self):
        channel = np.array([[0, 0, 255], [1, 1, 1]], dtype=np.uint8)
        hist = imhist256(channel)
        assert hist.shape == (256,)
        assert hist[0] == 2
        assert hist[1] == 3
        assert hist[255] == 1
        assert hist.sum() == channel.size

    def test_rejects_out_of_range_values(self):
        with pytest.raises(ValueError):
            imhist256(np.array([300]))

    def test_empty_input(self):
        hist = imhist256(np.array([], dtype=np.uint8))
        assert hist.sum() == 0
        assert hist.shape == (256,)


class TestAccumarraySum:
    def test_matches_naive_grouped_sum(self):
        bins = np.array([0, 0, 1, 2, 2, 2])
        values = np.array([1.0, 2.0, 5.0, 1.0, 1.0, 1.0])
        result = accumarray_sum(bins, values, n_bins=3)
        expected = np.array([3.0, 5.0, 3.0])
        np.testing.assert_allclose(result, expected)

    def test_empty_bin_is_zero(self):
        bins = np.array([0, 2])
        values = np.array([1.0, 1.0])
        result = accumarray_sum(bins, values, n_bins=3)
        assert result[1] == 0.0

    def test_2d_input(self):
        bins = np.array([[0, 1], [1, 0]])
        values = np.array([[1.0, 2.0], [3.0, 4.0]])
        result = accumarray_sum(bins, values, n_bins=2)
        np.testing.assert_allclose(result, [5.0, 5.0])
