import numpy as np

from shine_color.luminance import lum_match


def test_output_matches_manually_computed_targets():
    a = np.array([[0.0, 10.0, 20.0, 30.0]])
    b = np.array([[100.0, 110.0, 120.0, 130.0]])

    mean_a, sd_a = a.mean(), a.std(ddof=1)
    mean_b, sd_b = b.mean(), b.std(ddof=1)
    target_mean = (mean_a + mean_b) / 2
    target_sd = (sd_a + sd_b) / 2

    expected_a = np.clip(np.round((a - mean_a) / sd_a * target_sd + target_mean), 0, 255)
    expected_b = np.clip(np.round((b - mean_b) / sd_b * target_sd + target_mean), 0, 255)

    out = lum_match([a, b])
    np.testing.assert_array_equal(out[0], expected_a.astype(np.uint8))
    np.testing.assert_array_equal(out[1], expected_b.astype(np.uint8))


def test_uses_sample_sd_not_population_sd():
    # image b is constant, so its SD is 0 under EITHER ddof convention --
    # that isolates the ddof effect entirely to image a's contribution to
    # the target SD and to its own normalization.
    a = np.array([[10.0, 20.0, 30.0]])
    b = np.array([[100.0, 100.0, 100.0]])

    sd_a_sample = a.std(ddof=1)
    sd_a_population = a.std(ddof=0)
    assert sd_a_sample != sd_a_population  # sanity: conventions differ here

    mean_a = a.mean()
    target_mean = (mean_a + 100.0) / 2
    target_sd_sample = sd_a_sample / 2  # (sd_a + sd_b) / 2, sd_b == 0

    expected_with_sample_sd = np.clip(
        np.round((a - mean_a) / sd_a_sample * target_sd_sample + target_mean), 0, 255
    ).astype(np.uint8)

    out = lum_match([a, b])
    np.testing.assert_array_equal(out[0], expected_with_sample_sd)


def test_constant_image_maps_to_target_mean_not_nan():
    constant = np.full((3, 3), 50.0)
    varying = np.array([[0.0, 100.0], [50.0, 25.0]])
    out = lum_match([constant, varying])

    target_mean = (50.0 + varying.mean()) / 2
    expected_constant_value = int(round(target_mean))
    assert np.all(out[0] == expected_constant_value)
    assert not np.isnan(out[0]).any()


def test_output_dtype_and_shape():
    a = np.array([[1.0, 2.0], [3.0, 4.0]])
    b = np.array([[5.0, 6.0], [7.0, 8.0]])
    out = lum_match([a, b])
    assert out[0].dtype == np.uint8
    assert out[0].shape == a.shape
    assert out[1].shape == b.shape
