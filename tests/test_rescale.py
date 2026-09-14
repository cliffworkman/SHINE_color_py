import numpy as np
import pytest

from shine_color.rescale import rescale


def test_ordinary_range_option1():
    images = [np.array([[0.0, 10.0]]), np.array([[90.0, 100.0]])]
    out = rescale(images, option=1)
    assert out[0].dtype == np.uint8
    assert out[0][0, 0] == 0    # global darkest maps to 0
    assert out[1][0, 1] == 255  # global brightest maps to 255


def test_differing_per_image_extrema_option1_uses_global_extrema():
    images = [np.array([[0.0, 10.0]]), np.array([[90.0, 100.0]])]
    out = rescale(images, option=1)
    # image A's own max (10) is far from the global bright (100), so it
    # should NOT be anywhere near saturated -- confirms extrema are read
    # from the whole set, not per-image.
    assert out[0][0, 1] < 50


def test_differing_per_image_extrema_option2_uses_mean_of_extrema():
    # image A: min=0 max=20; image B: min=80 max=100
    # avg_dark=(0+80)/2=40; avg_bright=(20+100)/2=60
    a = np.array([[0.0, 20.0]])
    b = np.array([[80.0, 100.0]])
    out = rescale([a, b], option=2)
    # both of A's own values (0, 20) sit below avg_dark=40 -> saturate to 0
    assert np.all(out[0] == 0)
    # both of B's own values (80, 100) sit above avg_bright=60 -> saturate to 255
    assert np.all(out[1] == 255)


def test_option2_overshoot_is_saturated_by_terminal_cast_only():
    a = np.array([[0.0, 10.0]])      # own extrema 0..10
    b = np.array([[10.0, 1000.0]])   # own extrema 10..1000, drags the mean bright far up
    out = rescale([a, b], option=2)
    # avg_dark=(0+10)/2=5, avg_bright=(10+1000)/2=505
    # a's pixel 0.0 -> (0-5)/500*255 = -2.55, legitimately negative pre-cast
    assert out[0][0, 0] == 0


def test_global_degenerate_range_propagates_nan_to_zero_under_option1():
    # Every image is the identical constant value -> global bright==dark
    # -> 0/0 = NaN for every pixel -> MATLAB's uint8(NaN) == 0.
    images = [np.full((2, 2), 7.0), np.full((2, 2), 7.0)]
    out = rescale(images, option=1)
    assert np.all(out[0] == 0)
    assert np.all(out[1] == 0)


def test_option2_can_hit_0_over_0_when_option1_does_not():
    # Three constant images at 0, 15, 30: each is individually constant
    # (own max==min), so avg_bright==avg_dark==15 for option 2 -- and
    # the middle image's own value (15) equals that shared average
    # exactly, giving a literal (15-15)/0 = 0/0 = NaN for it specifically
    # (which MATLAB's uint8(NaN) -- and this port's to_uint8 -- map to
    # 0), collapsing what should be a meaningful mid-range value to 0.
    # Option 1 uses the SET's true global extrema (0 and 30) instead, so
    # its span is non-degenerate and the middle image is rescaled
    # normally rather than collapsing.
    a = np.full((2, 2), 0.0)
    b = np.full((2, 2), 15.0)
    c = np.full((2, 2), 30.0)

    out1 = rescale([a, b, c], option=1)
    assert np.all(out1[0] == 0)
    assert np.all(out1[1] == 128)  # (15-0)/30*255 = 127.5 -> away-from-zero -> 128
    assert np.all(out1[2] == 255)

    out2 = rescale([a, b, c], option=2)
    assert np.all(out2[0] == 0)    # (0-15)/0 = -Inf -> saturates to 0
    assert np.all(out2[1] == 0)    # (15-15)/0 = NaN  -> maps to 0, NOT a mid-range value
    assert np.all(out2[2] == 255)  # (30-15)/0 = +Inf -> saturates to 255


def test_invalid_option_raises():
    with pytest.raises(ValueError):
        rescale([np.zeros((2, 2))], option=0)
    with pytest.raises(ValueError):
        rescale([np.zeros((2, 2))], option=3)
