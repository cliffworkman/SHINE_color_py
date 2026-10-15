"""Phase 1 evidence domains, imports, persistence, exports and local access."""

import csv
import json
import os
import urllib.request
import urllib.error
import zipfile
import numpy as np
import pytest
from shine_color import batch, io, diagnostics, histogram
from shine_color.numeric import imhist256, sample_std
from shine_color.review import compare_batch, open_report
from shine_color.review.state import ReviewState, ConflictError
from shine_color.review.server import ReviewServer


def make_batch(tmp_path, space="HSV", mode=1, iterations=1):
    source = tmp_path / "source"
    source.mkdir()
    rng = np.random.default_rng(88)
    for i in range(3):
        io.save_rgb(
            rng.integers(0, 256, (13, 17, 3), dtype=np.uint8), source / f"{i}.png"
        )
    result = batch.process_directory(
        source, tmp_path / "normalized", space, mode, iterations
    )
    return source, result


@pytest.fixture
def report(tmp_path):
    source, result = make_batch(tmp_path)
    return compare_batch(
        source,
        tmp_path / "normalized",
        manifest=result.manifest_path,
        review_dir=tmp_path / "review",
    )


def save_payload(report, **kw):
    s = report.data["stimuli"][0]
    return dict(
        project_id=report.data["project_id"],
        stimulus_id=s["stimulus_id"],
        pair_id=s["pair_id"],
        status="Flag",
        note='=review\n"hello", café',
        reviewer="Cliff",
        revision=0,
        **kw,
    )


@pytest.mark.parametrize("space", ["RGB", "HSV", "CIELab"])
@pytest.mark.parametrize("mode", [1, 2])
def test_modes_spaces_and_expected_targets(tmp_path, space, mode):
    source, result = make_batch(tmp_path, space, mode)
    before = {p: p.read_bytes() for p in source.iterdir()}
    report = compare_batch(
        source,
        result.manifest_path.parent,
        manifest=result.manifest_path,
        review_dir=tmp_path / "review",
    )
    assert before == {p: p.read_bytes() for p in source.iterdir()}
    arrays = [
        diagnostics.channels(io.load_rgb(p), space) for p in sorted(source.iterdir())
    ]
    for name in arrays[0]:
        c = report.data["stimuli"][0]["channels"][name]
        if mode == 1:
            assert c["target_mean"] == pytest.approx(
                np.mean([a[name].mean() for a in arrays])
            )
            assert c["target_sample_sd"] == pytest.approx(
                np.mean([sample_std(a[name]) for a in arrays])
            )
            assert c["target_histogram"] is None
        else:
            expected = histogram.hist_match(
                [a[name] for a in arrays], rng=np.random.default_rng(3)
            )
            assert c["target_histogram"] == imhist256(expected[0]).tolist()
    assert all(r["gamut_clip_fraction"] is None for r in report.data["stimuli"])
    assert all(
        "recorded_intermediate_mean" not in c
        for r in report.data["stimuli"]
        for c in r["channels"].values()
    )


def test_repeated_targets_unavailable(tmp_path):
    source, result = make_batch(tmp_path, iterations=2)
    r = compare_batch(
        source,
        result.manifest_path.parent,
        manifest=result.manifest_path,
        review_dir=tmp_path / "review",
    )
    c = r.data["stimuli"][0]["channels"]["V"]
    assert c["target_mean"] is None and c["target_provenance"].startswith("unavailable")


def test_metrics_known_and_nonmutating():
    a = np.zeros((130, 3, 3), dtype=np.uint8)
    b = np.full_like(a, 12)
    r = diagnostics.compare_pair(a, b, "RGB")
    assert r["rgb_rmse"] == 12 and r["channels"]["R"]["delta_mean"] == 12
    assert r["channels"]["R"]["post_saved"]["sample_sd"] == 0
    assert r["channels"]["R"]["histogram_total_variation"] == 1
    assert not a.any()
    assert diagnostics.histogram_stats([1] + [0] * 255)["sample_sd"] == 0
    with pytest.raises(ValueError):
        diagnostics.compare_pair(a, b[:2], "HSV")


def test_native_mixed_dimensions_and_recorded_stats(tmp_path):
    source = tmp_path / "s"
    source.mkdir()
    output = tmp_path / "o"
    output.mkdir()
    inputs = []
    outputs = []
    for i, shape in enumerate([(2, 3, 3), (4, 5, 3)]):
        rgb = np.full(shape, 50 + i * 100, dtype=np.uint8)
        io.save_rgb(rgb, source / f"{i}.png")
        io.save_rgb(rgb, output / f"{i}.png")
        _, a = io._read_rgb(source / f"{i}.png")
        _, b = io._read_rgb(output / f"{i}.png")
        inputs.append(a)
        outputs.append(
            dict(
                filename=b["name"],
                source_name=a["name"],
                file_sha256=b["file_sha256"],
                pixel_sha256=b["pixel_sha256"],
                dimensions=b["dimensions"],
                working_L_after={"mean": 42, "sample_sd": 3},
                rgb_out_of_gamut_pixel_fraction=0.2,
                working_L_clipped_fraction=0.1,
            )
        )
    m = dict(
        schema_version=1,
        workflow="native_dimension_CIELab_luminance_batch",
        pipeline=dict(colorspace="CIELab", mode=1, iterations=1),
        group=dict(count=2),
        inputs=inputs,
        outputs=outputs,
    )
    manifest = output / "manifest.json"
    manifest.write_text(json.dumps(m))
    r = compare_batch(source, output, manifest=manifest, review_dir=tmp_path / "r")
    assert [s["width"] for s in r.data["stimuli"]] == [3, 5]
    c = r.data["stimuli"][0]["channels"]["L"]
    assert c["post_minus_recorded_mean"] == c["post_saved"]["mean"] - 42
    assert r.data["stimuli"][0]["gamut_clip_fraction"] == 0.2
    assert r.data["summary"]["L"]["pre"]["mean_of_image_means"] == np.mean(
        [s["channels"]["L"]["pre"]["mean"] for s in r.data["stimuli"]]
    )


@pytest.mark.parametrize(
    "damage", ["hash", "dimension", "duplicate", "path", "spectral", "order", "missing"]
)
def test_reject_bad_import(tmp_path, damage):
    source, result = make_batch(tmp_path)
    m = result.manifest
    if damage == "hash":
        m["inputs"][0]["file_sha256"] = "wrong"
    if damage == "dimension":
        m["outputs"][0]["dimensions"] = [1, 1]
    if damage == "duplicate":
        m["inputs"][1]["name"] = m["inputs"][0]["name"]
    if damage == "path":
        m["inputs"][0]["name"] = "../evil.png"
        m["group"]["ordered_input_names"][0] = "../evil.png"
    if damage == "spectral":
        m["pipeline"]["mode"] = 3
    if damage == "order":
        m["group"]["ordered_input_names"].reverse()
    if damage == "missing":
        m["outputs"].pop()
    result.manifest_path.write_text(json.dumps(m))
    with pytest.raises((ValueError, FileNotFoundError)):
        compare_batch(
            source,
            result.manifest_path.parent,
            manifest=result.manifest_path,
            review_dir=tmp_path / "review",
        )
    assert not (tmp_path / "review").exists()


def test_persistence_conflicts_and_pair_binding(report):
    state = ReviewState(report)
    p = save_payload(report)
    first = state.save(p)
    assert first["revision"] == 1
    assert (
        ReviewState(open_report(report.root)).snapshot()["decisions"][p["stimulus_id"]][
            "note"
        ]
        == p["note"]
    )
    with pytest.raises(ConflictError):
        state.save(p)
    p["revision"] = 1
    p["status"] = "Accept"
    state.save(p)
    assert len(state.snapshot()["events"]) == 2
    p["pair_id"] = "changed"
    with pytest.raises(ValueError, match="pair"):
        state.save(p)


@pytest.mark.parametrize(
    "key,value",
    [
        ("status", "Auto accept"),
        ("note", 23),
        ("revision", True),
        ("project_id", "other"),
        ("reviewer", None),
    ],
)
def test_invalid_decisions(report, key, value):
    p = save_payload(report)
    p[key] = value
    with pytest.raises(ValueError):
        ReviewState(report).save(p)
    assert not ReviewState(report).snapshot()["events"]


def test_exports_roundtrip_and_portable(report, tmp_path):
    p = save_payload(report)
    ReviewState(report).save(p)
    report.to_json(tmp_path / "export.json")
    report.to_csv(tmp_path / "export.csv")
    data = json.loads((tmp_path / "export.json").read_text())
    assert data["review"]["decisions"][p["stimulus_id"]]["note"] == p["note"]
    with (tmp_path / "export.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 3 and rows[0]["review_note"] == "'" + p["note"]
    assert rows[0]["gamut_clip_fraction"] == ""
    for images in [False, True]:
        dest = tmp_path / f"{images}.zip"
        report.export(dest, images)
        with zipfile.ZipFile(dest) as z:
            assert "index.html" in z.namelist() and "review_state.csv" in z.namelist()
            assert any(n.startswith("images/") for n in z.namelist()) == images
            assert (
                json.loads(z.read("review_state.json"))["decisions"][p["stimulus_id"]][
                    "status"
                ]
                == "Flag"
            )
        with pytest.raises(FileExistsError):
            report.export(dest, images)


def test_http_local_security_and_saving(report):
    server = ReviewServer(report.root)
    try:

        def get(path, headers=None):
            return urllib.request.urlopen(
                urllib.request.Request(server.origin + path, headers=headers or {})
            )

        session = json.load(get("/api/session"))
        assert session["token"]
        assert get("/").status == 200
        assert get("/app.js").headers.get_content_type() == "text/javascript"
        assert get("/style.css").headers.get_content_type() == "text/css"
        for path in [
            "/../review.sqlite3",
            "/review.sqlite3",
            "/report.json",
            "/%2e%2e/README.md",
        ]:
            with pytest.raises(urllib.error.HTTPError):
                get(path)
        with pytest.raises(urllib.error.HTTPError):
            get("/", {"Host": "attacker.test"})
        payload = json.dumps(save_payload(report)).encode()
        request = urllib.request.Request(
            server.origin + "/api/decision",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(request)
        assert e.value.code == 403
        request.add_header("Origin", server.origin)
        request.add_header("X-Review-Token", session["token"])
        assert json.load(urllib.request.urlopen(request))["revision"] == 1
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(request)
        assert e.value.code == 409
        assert "Flag" in get("/api/export.csv").read().decode()
    finally:
        server.close()


def test_tampered_asset_refuses_server(report):
    (report.root / report.data["stimuli"][0]["before_image"]).write_bytes(b"changed")
    with pytest.raises(ValueError, match="changed"):
        ReviewServer(report.root)


def test_failed_export_leaves_no_partial_archive(report, tmp_path):
    (report.root / report.data["stimuli"][0]["before_image"]).write_bytes(b"changed")
    destination = tmp_path / "failed.zip"
    with pytest.raises(ValueError, match="changed"):
        report.export(destination, True)
    assert not destination.exists()
    assert not list(tmp_path.glob(".review-export-*"))


def test_publication_lock_retains_complete_review(tmp_path, monkeypatch):
    from shine_color.review import project

    source, result = make_batch(tmp_path)

    def locked(*args):
        raise PermissionError("Simulated folder lock")

    monkeypatch.setattr(project.os, "rename", locked)
    monkeypatch.setattr(project.time, "sleep", lambda delay: None)
    with pytest.raises(RuntimeError, match="Completed project retained"):
        compare_batch(
            source,
            result.manifest_path.parent,
            manifest=result.manifest_path,
            review_dir=tmp_path / "review",
        )
    retained = list(tmp_path.glob(".shine-review-*"))
    assert len(retained) == 1
    recovered = open_report(retained[0], verify_assets=True)
    assert len(recovered.data["stimuli"]) == 3
    assert recovered.state()["decisions"] == {}
    assert not (tmp_path / "review").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows publication retry")
def test_transient_windows_publication_lock_recovers(tmp_path, monkeypatch):
    from shine_color.review import project

    stage = tmp_path / "stage"
    stage.mkdir()
    (stage / "proof.txt").write_text("complete")
    destination = tmp_path / "published"
    rename = project.os.rename
    calls = []
    delays = []

    def transient(source, target):
        calls.append((source, target))
        if len(calls) <= 2:
            raise PermissionError("Transient sharing lock")
        return rename(source, target)

    monkeypatch.setattr(project.os, "rename", transient)
    monkeypatch.setattr(project.time, "sleep", delays.append)
    project._publish_directory(stage, destination)
    assert len(calls) == 3 and delays == [0.1, 0.2]
    assert (destination / "proof.txt").read_text() == "complete"
    assert not stage.exists()


def test_cleanup_lock_does_not_hide_import_error(tmp_path, monkeypatch):
    from shine_color.review import project

    source, result = make_batch(tmp_path)
    result.manifest["inputs"][0]["file_sha256"] = "changed"
    result.manifest_path.write_text(json.dumps(result.manifest))

    def locked(*args):
        raise PermissionError("Simulated cleanup lock")

    monkeypatch.setattr(project.shutil, "rmtree", locked)
    with pytest.warns(RuntimeWarning, match="could not be removed"):
        with pytest.raises(ValueError, match="file_sha256 mismatch"):
            compare_batch(
                source,
                result.manifest_path.parent,
                manifest=result.manifest_path,
                review_dir=tmp_path / "review",
            )
