"""Read-only, domain-explicit measurements for review; no normalization calls."""

import math
import numpy as np
from . import color


def channels(rgb, colorspace):
    space = colorspace.lower()
    if space == "rgb":
        return dict(zip(("R", "G", "B"), color.split_rgb(rgb)))
    if space == "hsv":
        return {"V": color.split_hsv(rgb)[2]}
    if space in ("lab", "cielab"):
        return {"L": color.split_lab(rgb)[0]}
    raise ValueError("Unsupported colorspace")


def histogram_stats(counts):
    h = np.asarray(counts, dtype=np.float64)
    n = float(h.sum())
    if h.shape != (256,) or n <= 0 or np.any(h < 0) or not np.isfinite(h).all():
        raise ValueError("Expected 256 nonnegative counts with positive total")
    levels = np.arange(256, dtype=np.float64)
    mean = float(h @ levels / n)
    sd = math.sqrt(float(h @ ((levels - mean) ** 2)) / (n - 1)) if n > 1 else 0.0
    return dict(
        mean=mean,
        sample_sd=sd,
        zero_fraction=float(h[0] / n),
        maximum_fraction=float(h[-1] / n),
        histogram=h.astype(np.int64).tolist(),
    )


def total_variation(a, b):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    return float(np.abs(a / a.sum() - b / b.sum()).sum() / 2)


def compare_pair(before, after, colorspace):
    """Compare aligned decoded RGB arrays; work in strips, never resize.

    L and V are SHINE uint8 working channels (0..255), not physical luminance.
    Post values are re-extracted from saved-output RGB, not intermediate arrays.
    """
    if (
        before.shape != after.shape
        or before.dtype != np.uint8
        or after.dtype != np.uint8
    ):
        raise ValueError(
            "Pairs must have identical RGB uint8 dimensions; no implicit resizing"
        )
    if before.ndim != 3 or before.shape[2] != 3 or not before.size:
        raise ValueError("Expected nonempty RGB arrays")
    histograms, squared, rgb_squared = {}, {}, 0.0
    for start in range(0, len(before), 64):
        a, b = before[start : start + 64], after[start : start + 64]
        delta = b.astype(float) - a.astype(float)
        rgb_squared += float(np.sum(delta * delta))
        ca, cb = channels(a, colorspace), channels(b, colorspace)
        for name in ca:
            if name not in histograms:
                histograms[name] = [
                    np.zeros(256, dtype=np.int64),
                    np.zeros(256, dtype=np.int64),
                ]
                squared[name] = 0.0
            for h, values in zip(histograms[name], (ca[name], cb[name])):
                h += np.bincount(values.ravel(), minlength=256)
            delta = cb[name].astype(float) - ca[name].astype(float)
            squared[name] += float(np.sum(delta * delta))
    result = {}
    for name, (ha, hb) in histograms.items():
        pre, post = histogram_stats(ha), histogram_stats(hb)
        result[name] = dict(
            pre=pre,
            post_saved=post,
            delta_mean=post["mean"] - pre["mean"],
            delta_sample_sd=post["sample_sd"] - pre["sample_sd"],
            rmse=math.sqrt(squared[name] / (before.size / 3)),
            histogram_total_variation=total_variation(ha, hb),
        )
    return dict(rgb_rmse=math.sqrt(rgb_squared / before.size), channels=result)
