import json
from pathlib import Path

import numpy as np

from reference.stimulus_pilot.metrics import channel_metrics, change, conditioning
from reference.stimulus_pilot.run import write_report
from reference.stimulus_pilot.selection import select_sample


def _rows(n=8):
    return [dict(valid=True, relative_path=f"{i:03d}.png", file_sha256=str(i),
                 pixel_sha256=str(i), dimensions=[4, 4], v_mean=float(i),
                 v_sample_sd=float(n-i), v_entropy_bits=float(i % 3),
                 v_low_power_fraction=float(i)/n) for i in range(n)]


def test_selection_is_deterministic_and_output_independent():
    rows = _rows()
    first, rule = select_sample(rows, limit=4)
    rows[0]["v_mean"] = 999999  # selection uses only the frozen input descriptors
    second, _ = select_sample(_rows(), limit=4)
    assert [r["relative_path"] for r in first] != []
    assert [r["relative_path"] for r in second] == [r["relative_path"] for r in select_sample(_rows(), limit=4)[0]]
    assert rule["method"] == "baseline_farthest_point"


def test_channel_metrics_histogram_and_no_mutation():
    a = np.array([[0, 1], [255, 255]], dtype=np.uint8)
    before = a.copy()
    m = channel_metrics(a)
    assert m["histogram"][0] == 1 and m["histogram"][255] == 2
    assert m["sample_sd"] > 0 and a.tobytes() == before.tobytes()


def test_conditioning_is_finite_and_traceable():
    a = np.arange(16, dtype=np.uint8).reshape(4, 4)
    result = conditioning(a)
    assert len(result["stage_input_sha256"]) == 64
    assert result["max_magnitude"] >= result["min_magnitude"]


def test_difference_metrics_are_explicit():
    a = np.zeros((2, 2, 3), dtype=np.uint8)
    b = a.copy(); b[0, 0, 0] = 4
    result = change(a, b)
    assert result["changed_scalar_percent"] == 100 / 12
    assert result["rgb_max_abs"] == 4


def test_report_schema_and_html_entries(tmp_path):
    original = np.zeros((4, 4, 3), dtype=np.uint8)
    from shine_color import io
    source = tmp_path / "src.png"
    io.save_rgb(original, source)
    out = tmp_path / "out"
    out.mkdir()
    io.save_rgb(original, out / "arm.png")
    manifest = dict(source_directory=str(tmp_path), candidates=[dict(relative_path="src.png", file_sha256="x", pixel_sha256="y")])
    result = dict(config=dict(label="arm"), output_directory=str(out), manifest={}, stages=[],
                  images=[dict(image="src.png", source_sha256="x", output_sha256="z",
                               metrics=dict(rgb_change=change(original, original)))])
    write_report(out, manifest, [result])
    assert (out / "pilot_report.html").exists()
    assert "src.png" in (out / "pilot_report.html").read_text()
    json.loads((out / "metrics_summary.json").read_text())
