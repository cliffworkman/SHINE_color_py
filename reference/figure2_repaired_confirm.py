"""Compact Figure 2 confirmation for the repaired SHINE_color 0.0.6 snapshot.

This consumes the already-frozen lossless RGB MAT inputs from the Figure 2
audit. It does not decode JPEGs in the common-input paths and does not modify
either reference checkout.
"""
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from scipy.io import loadmat

from .figure2_audit import _octave, _reference, compare_records


EXPECTED_COMMIT = "870e058fe8bf1e4090baf2401ff0e127d1c0237a"
HISTORICAL_COMMIT = "330a9be6e49f59e5d68fb985744b2a50c278e8d8"


def _sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def _tree_manifest(root, normalize_text=False):
    root = Path(root)
    rows = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        data = path.read_bytes()
        if normalize_text:
            data = data.replace(b"\r\n", b"\n")
        rows.append(f"{path.relative_to(root).as_posix()}\0{_sha_bytes(data)}")
    encoded = "\n".join(rows).encode()
    return dict(files=len(rows), sha256=_sha_bytes(encoded))


def _hash_lists(values):
    return [_sha_bytes(np.asarray(value, dtype=np.int64).tobytes()) for value in values]


def _target_hash(value):
    return _sha_bytes(np.asarray(value, dtype=np.int64).tobytes())


def _sorted_hashes(values):
    return [_sha_bytes(np.asarray(value).tobytes()) for value in values]


def _summary(record, sorted_hashes):
    return dict(
        pre_histogram_hashes=_hash_lists(record["pre"]["histograms"]),
        target_hash=_target_hash(record["target"]),
        post_histogram_hashes=_hash_lists(record["post"]["histograms"]),
        sorted_post_hashes=list(sorted_hashes),
        post_statistics=record["post"]["statistics"],
    )


def _parity(left, right, left_sorted, right_sorted):
    comparison = compare_records(left, right, left_sorted, right_sorted)
    comparison["post_statistics_exact"] = bool(
        np.array_equal(np.asarray(left["post"]["statistics"]),
                       np.asarray(right["post"]["statistics"]))
    )
    comparison["post_statistics_max_abs_difference"] = float(
        np.max(np.abs(np.asarray(left["post"]["statistics"])
                      - np.asarray(right["post"]["statistics"])))
    )
    return comparison


def _hash_parity(left, right, left_sorted_hashes, right_sorted_hashes):
    result = dict(
        pre_histograms_equal=left["pre"]["histograms"] == right["pre"]["histograms"],
        target_histogram_equal=left["target"] == right["target"],
        post_histograms_equal=left["post"]["histograms"] == right["post"]["histograms"],
        within_left_post_equal=all(h == left["post"]["histograms"][0]
                                   for h in left["post"]["histograms"]),
        within_right_post_equal=all(h == right["post"]["histograms"][0]
                                    for h in right["post"]["histograms"]),
        sorted_values_equal=list(left_sorted_hashes) == list(right_sorted_hashes),
        post_statistics_exact=bool(np.array_equal(
            np.asarray(left["post"]["statistics"]),
            np.asarray(right["post"]["statistics"]))),
        post_statistics_max_abs_difference=float(np.max(np.abs(
            np.asarray(left["post"]["statistics"])
            - np.asarray(right["post"]["statistics"])))),
    )
    result["passes"] = all(result[k] for k in (
        "pre_histograms_equal", "target_histogram_equal", "post_histograms_equal",
        "within_left_post_equal", "within_right_post_equal", "sorted_values_equal"))
    return result


def _cells_from_mat(path):
    data = loadmat(path)["rgb"].ravel()
    return [np.asarray(item, dtype=np.uint8) for item in data]


def _archived_sorted(path):
    data = loadmat(path)["sorted_post"].ravel()
    return [np.asarray(item).ravel().astype(np.uint8) for item in data]


def _natural_jpeg(octave, toolbox, samples, destination):
    destination = Path(destination)
    _octave(octave,
            f"export_figure2_jpeg({_quote(toolbox)},{_quote(samples)},"
            f"{_quote(destination)});",
            destination.with_suffix(".log"))
    data = loadmat(destination)
    return dict(
        pre=dict(histograms=data["pre_hist"].T.astype(int).tolist(),
                 statistics=data["pre_stats"].tolist()),
        post=dict(histograms=data["post_hist"].T.astype(int).tolist(),
                  statistics=data["post_stats"].tolist()),
        version=str(data["octave_version"].item()),
    )


def _quote(path):
    return "'" + str(Path(path).resolve()).replace("\\", "/").replace("'", "''") + "'"


def run(samples, destination, octave, repaired_toolbox, historical_toolbox,
        audit_artifact=None, fork_checkout=None):
    project = Path(__file__).parents[1].resolve()
    samples = Path(samples).resolve()
    destination = Path(destination).resolve()
    repaired_toolbox = Path(repaired_toolbox).resolve()
    historical_toolbox = Path(historical_toolbox).resolve()
    audit_artifact = (Path(audit_artifact) if audit_artifact else
                      project / "reference/.cache/figure2_audit_20260916").resolve()
    fork_checkout = (Path(fork_checkout) if fork_checkout else
                     project.parent / "SHINE_color_fork").resolve()
    destination.mkdir(parents=True, exist_ok=False)

    if EXPECTED_COMMIT not in repaired_toolbox.parent.name:
        raise ValueError("repaired toolbox is not the named 0.0.6 snapshot")
    if "version 0.0.6" not in (repaired_toolbox.parent / "README.md").read_text(encoding="utf-8"):
        raise ValueError("repaired snapshot does not identify version 0.0.6")

    fork_head = subprocess.check_output(
        ["git", "-C", str(fork_checkout), "rev-parse", "HEAD"], text=True).strip()
    fork_status = subprocess.check_output(
        ["git", "-C", str(fork_checkout), "status", "--porcelain"], text=True)
    snapshot_tree = _tree_manifest(repaired_toolbox)
    fork_tree = _tree_manifest(fork_checkout / "toolbox")
    snapshot_tree_normalized = _tree_manifest(repaired_toolbox, normalize_text=True)
    fork_tree_normalized = _tree_manifest(fork_checkout / "toolbox", normalize_text=True)
    if fork_status:
        raise RuntimeError("sibling repaired fork is not clean")

    metrics = json.loads((audit_artifact / "figure2_reproduction_metrics.json").read_text())
    paths = {}
    for name in ("pillow", "octave"):
        source = audit_artifact / f"{name}_rgb.mat"
        repaired_mat = destination / f"{name}_repaired.mat"
        historical_mat = destination / f"{name}_historical.mat"
        repaired, repaired_sorted = _reference(octave, repaired_toolbox, source, repaired_mat)
        historical, historical_sorted = _reference(octave, historical_toolbox, source, historical_mat)
        archived = metrics["paths"][name]
        archived_octave = archived["octave"]
        archived_historical = archived["historical"]
        archived_python = archived["python"]
        existing_sorted = _archived_sorted(audit_artifact / name / "reference.mat")
        python_sorted_hashes = archived["sorted_post_sha256"]
        paths[name] = dict(
            repaired=_summary(repaired, _sorted_hashes(repaired_sorted)),
            historical=_summary(historical, _sorted_hashes(historical_sorted)),
            python=_summary(archived_python, python_sorted_hashes),
            octave_reference=_summary(archived_octave, _sorted_hashes(existing_sorted)),
            repaired_vs_historical=_parity(repaired, historical, repaired_sorted, historical_sorted),
            repaired_vs_python=_parity(repaired, archived_python, repaired_sorted,
                                        [np.array([], dtype=np.uint8)] * 3),
            repaired_vs_octave_reference=_parity(repaired, archived_octave, repaired_sorted,
                                                 existing_sorted),
            historical_vs_repaired=_parity(historical, repaired, historical_sorted, repaired_sorted),
            historical_vs_python=_parity(historical, archived_python, historical_sorted,
                                         [np.array([], dtype=np.uint8)] * 3),
        )
        # Python sorted arrays are archived by hash; compare those hashes explicitly.
        paths[name]["repaired_vs_python"]["sorted_values_equal"] = [
            _sha_bytes(np.asarray(value).tobytes()) == expected
            for value, expected in zip(repaired_sorted, python_sorted_hashes)
        ]
        paths[name]["historical_vs_python"]["sorted_values_equal"] = [
            _sha_bytes(np.asarray(value).tobytes()) == expected
            for value, expected in zip(historical_sorted, python_sorted_hashes)
        ]
        paths[name]["repaired_vs_python"]["passes"] = all([
            paths[name]["repaired_vs_python"][key]
            for key in ("pre_histograms_equal", "target_histogram_equal",
                        "post_histograms_equal", "within_python_post_equal",
                        "within_reference_post_equal")
        ]) and all(paths[name]["repaired_vs_python"]["sorted_values_equal"])
        paths[name]["historical_vs_python"]["passes"] = all([
            paths[name]["historical_vs_python"][key]
            for key in ("pre_histograms_equal", "target_histogram_equal",
                        "post_histograms_equal", "within_python_post_equal",
                        "within_reference_post_equal")
        ]) and all(paths[name]["historical_vs_python"]["sorted_values_equal"])

    natural = _natural_jpeg(octave, repaired_toolbox, samples, destination / "natural_jpeg.mat")
    report = dict(
        schema_version=1,
        scope="0.0.6 Figure 2 mode-2 common-input confirmation",
        settings=dict(colorspace="HSV", mode=2, iterations=1, rescale_option=1,
                      rescale_ignored=True, group_size=3, ties="stochastic_unseeded"),
        repaired_commit=EXPECTED_COMMIT,
        repaired_snapshot=repaired_toolbox.name,
        historical_commit=HISTORICAL_COMMIT,
        fork_checkout_head=fork_head,
        fork_checkout_clean=True,
        toolbox_tree=snapshot_tree,
        toolbox_tree_normalized=snapshot_tree_normalized,
        clean_fork_toolbox_tree_normalized=fork_tree_normalized,
        snapshot_matches_clean_fork_toolbox=snapshot_tree_normalized == fork_tree_normalized,
        clean_fork_toolbox_tree=fork_tree,
        paths=paths,
        natural_jpeg=natural,
        publication=dict(baseline=[["172.47", "44.72"], ["80.34", "127.26"],
                                   ["127.26", "76.76"]], post=["126.69", "74.77"]),
    )
    if snapshot_tree != _tree_manifest(repaired_toolbox):
        raise RuntimeError("repaired snapshot changed during read-only confirmation")
    (destination / "figure2_repaired_confirmation.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return report


def run_archived(destination, repaired_toolbox, fork_checkout=None,
                 audit_artifact=None):
    """Validate the external Octave results already archived by commit 3be131e.

    This path is used when GNU Octave is unavailable. The archived ``octave``
    record is explicitly tagged with EXPECTED_COMMIT by the prior audit; no
    new runtime result is claimed here.
    """
    project = Path(__file__).parents[1].resolve()
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=False)
    repaired_toolbox = Path(repaired_toolbox).resolve()
    audit_artifact = (Path(audit_artifact) if audit_artifact else
                      project / "reference/.cache/figure2_audit_20260916").resolve()
    fork_checkout = (Path(fork_checkout) if fork_checkout else
                     project.parent / "SHINE_color_fork").resolve()
    metrics = json.loads((audit_artifact / "figure2_reproduction_metrics.json").read_text())
    if metrics["reference_commit"] != EXPECTED_COMMIT:
        raise RuntimeError("archived Octave reference is not the requested repaired commit")
    fork_head = subprocess.check_output(
        ["git", "-C", str(fork_checkout), "rev-parse", "HEAD"], text=True).strip()
    fork_status = subprocess.check_output(
        ["git", "-C", str(fork_checkout), "status", "--porcelain"], text=True)
    snapshot_tree = _tree_manifest(repaired_toolbox)
    fork_tree = _tree_manifest(fork_checkout / "toolbox")
    snapshot_tree_normalized = _tree_manifest(repaired_toolbox, normalize_text=True)
    fork_tree_normalized = _tree_manifest(fork_checkout / "toolbox", normalize_text=True)
    if fork_status:
        raise RuntimeError("sibling repaired fork is not clean")
    paths = {}
    for name in ("pillow", "octave"):
        archived = metrics["paths"][name]
        repaired = archived["octave"]
        historical = archived["historical"]
        python = archived["python"]
        repaired_sorted = _archived_sorted(audit_artifact / name / "reference.mat")
        historical_sorted = _archived_sorted(audit_artifact / name / "historical.mat")
        repaired_hashes = _sorted_hashes(repaired_sorted)
        historical_hashes = _sorted_hashes(historical_sorted)
        python_hashes = archived["sorted_post_sha256"]
        paths[name] = dict(
            repaired=_summary(repaired, repaired_hashes),
            historical=_summary(historical, historical_hashes),
            python=_summary(python, python_hashes),
            octave_reference=_summary(repaired, repaired_hashes),
            repaired_vs_historical=_hash_parity(repaired, historical, repaired_hashes,
                                                 historical_hashes),
            repaired_vs_python=_hash_parity(repaired, python, repaired_hashes, python_hashes),
            repaired_vs_octave_reference=_hash_parity(repaired, repaired, repaired_hashes,
                                                      repaired_hashes),
            historical_vs_python=_hash_parity(historical, python, historical_hashes,
                                              python_hashes),
        )
    report = dict(
        schema_version=1,
        scope="0.0.6 Figure 2 archived common-input confirmation",
        archived_external_reference=True,
        runtime_note="No GNU Octave executable was available for a fresh rerun; repaired results are the existing external audit record.",
        settings=dict(colorspace="HSV", mode=2, iterations=1, rescale_option=1,
                      rescale_ignored=True, group_size=3, ties="stochastic_unseeded"),
        repaired_commit=EXPECTED_COMMIT,
        repaired_snapshot=repaired_toolbox.name,
        historical_commit=HISTORICAL_COMMIT,
        fork_checkout_head=fork_head,
        fork_checkout_clean=True,
        toolbox_tree=snapshot_tree,
        toolbox_tree_normalized=snapshot_tree_normalized,
        clean_fork_toolbox_tree=fork_tree,
        clean_fork_toolbox_tree_normalized=fork_tree_normalized,
        snapshot_matches_clean_fork_toolbox=snapshot_tree_normalized == fork_tree_normalized,
        paths=paths,
        natural_jpeg=None,
        publication=dict(baseline=[["172.47", "44.72"], ["80.34", "127.26"],
                                   ["127.26", "76.76"]], post=["126.69", "74.77"]),
    )
    (destination / "figure2_repaired_confirmation.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples")
    parser.add_argument("--destination", required=True)
    parser.add_argument("--octave", default="octave")
    parser.add_argument("--repaired-toolbox", required=True)
    parser.add_argument("--historical-toolbox", required=True)
    parser.add_argument("--archived-only", action="store_true")
    args = parser.parse_args()
    if args.archived_only:
        result = run_archived(args.destination, args.repaired_toolbox)
    else:
        if not args.samples:
            parser.error("--samples is required unless --archived-only is used")
        result = run(args.samples, args.destination, args.octave,
                     args.repaired_toolbox, args.historical_toolbox)
    print(json.dumps({"repaired_commit": result["repaired_commit"],
                      "paths": {k: v["repaired_vs_historical"] for k, v in result["paths"].items()}},
                     indent=2))
