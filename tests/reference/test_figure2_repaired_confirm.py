"""Offline checks for the archived repaired 0.0.6 Figure 2 confirmation."""
import json
from pathlib import Path

import pytest


DATA = json.loads((Path(__file__).parent / "fixtures" /
                   "figure2_repaired_confirmation.json").read_text())


@pytest.mark.parametrize("path", ["pillow", "octave"])
def test_repaired_commit_and_common_input_contract(path):
    assert DATA["repaired_commit"] == "870e058fe8bf1e4090baf2401ff0e127d1c0237a"
    assert DATA["fork_checkout_clean"]
    record = DATA["paths"][path]
    assert record["repaired_vs_historical"]["passes"]
    assert record["repaired_vs_python"]["passes"]
    assert record["repaired_vs_octave_reference"]["passes"]


@pytest.mark.parametrize("path", ["pillow", "octave"])
def test_repaired_and_historical_hashes_are_identical(path):
    record = DATA["paths"][path]
    for stage in ("pre_histogram_hashes", "target_hash", "post_histogram_hashes",
                  "sorted_post_hashes"):
        assert record["repaired"][stage] == record["historical"][stage]
        assert record["repaired"][stage] == record["python"][stage]
        assert record["repaired"][stage] == record["octave_reference"][stage]


@pytest.mark.parametrize("path,expected", [
    ("pillow", [["126.69", "74.77"]] * 3),
    ("octave", [["126.70", "74.78"]] * 3),
])
def test_post_statistics_remain_decoder_dependent(path, expected):
    stats = DATA["paths"][path]["repaired"]["post_statistics"]
    assert [[f"{mean:.2f}", f"{sd:.2f}"] for mean, sd in stats] == expected


def test_natural_jpeg_path_is_explicitly_unrun_without_octave():
    assert DATA["natural_jpeg"] is None
    assert DATA["archived_external_reference"]
