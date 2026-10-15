"""Verified pair import, review artifacts, and portable exports."""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import csv
import hashlib
import io as stdio
import json
import os
import shutil
import tempfile
import zipfile
import numpy as np
from PIL import Image
from .. import io, diagnostics
from ..numeric import matlab_round
from ..batch import _software

SCHEMA = 1
STATUSES = ("Unreviewed", "Accept", "Flag", "Reject")


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(
        value, sort_keys=True, allow_nan=False, ensure_ascii=True
    ).encode()


def write_json(path, value):
    path = Path(path)
    fd, tmp = tempfile.mkstemp(prefix=".review-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(value, f, indent=2, allow_nan=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def contained(root, relative):
    root = Path(root).resolve()
    p = Path(relative)
    if p.is_absolute() or p.drive or ".." in p.parts or not p.parts:
        raise ValueError("Expected a contained relative path")
    path = root / p
    if not path.resolve().is_relative_to(root):
        raise ValueError("Path escapes selected directory")
    return path


def csv_text(rows):
    buf = stdio.StringIO(newline="")
    if not rows:
        return ""
    writer = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\r\n")
    writer.writeheader()
    for row in rows:
        safe = {
            k: (
                "'" + v
                if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@"))
                else v
            )
            for k, v in row.items()
        }
        writer.writerow(safe)
    return buf.getvalue()


def table_rows(data, state=None):
    decisions = (state or {}).get("decisions", {})
    rows = []
    for item in data["stimuli"]:
        d = decisions.get(item["stimulus_id"], {})
        row = {
            k: item[k]
            for k in (
                "stimulus_id",
                "pair_id",
                "run_id",
                "input_path",
                "output_path",
                "width",
                "height",
                "input_sha256",
                "output_sha256",
                "rgb_rmse",
            )
        }
        for name, c in item["channels"].items():
            for prefix, values in [("pre", c["pre"]), ("post_saved", c["post_saved"])]:
                row[f"{prefix}_{name}_mean"] = values["mean"]
                row[f"{prefix}_{name}_sample_sd"] = values["sample_sd"]
            for key in (
                "delta_mean",
                "delta_sample_sd",
                "rmse",
                "histogram_total_variation",
                "target_mean",
                "target_sample_sd",
                "post_target_delta_mean",
                "post_target_delta_sample_sd",
                "post_target_histogram_total_variation",
                "recorded_intermediate_mean",
                "recorded_intermediate_sample_sd",
                "post_minus_recorded_mean",
                "post_minus_recorded_sample_sd",
            ):
                row[f"{name}_{key}"] = c.get(key)
            row[f"{name}_target_provenance"] = c["target_provenance"]
        row.update(
            gamut_clip_fraction=item.get("gamut_clip_fraction"),
            gamut_clip_provenance=item["gamut_clip_provenance"],
            working_L_clip_fraction=item.get("working_L_clip_fraction"),
            review_status=d.get("status", "Unreviewed"),
            review_note=d.get("note", ""),
            reviewer=d.get("reviewer", ""),
            review_revision=d.get("revision", 0),
            reviewed_at=d.get("updated_at", ""),
        )
        rows.append(row)
    return rows


@dataclass
class Report:
    root: Path
    data: dict

    def state(self):
        from .state import ReviewState

        return ReviewState(self).snapshot()

    def to_csv(self, path):
        Path(path).write_text(
            csv_text(table_rows(self.data, self.state())),
            encoding="utf-8-sig",
            newline="",
        )

    def to_json(self, path):
        write_json(path, {"report": self.data, "review": self.state()})

    def export(self, destination, include_images=False):
        """New ZIP snapshot: JSON preserves exact text; CSV is spreadsheet-safe."""
        destination = Path(destination)
        if destination.exists():
            raise FileExistsError(destination)
        snapshot = self.state()
        data = dict(
            self.data,
            exported_at=now(),
            embedded_review=snapshot,
            portable_images=bool(include_images),
        )
        fd, temporary = tempfile.mkstemp(
            prefix=".review-export-", suffix=".zip", dir=destination.parent
        )
        os.close(fd)
        try:
            with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as z:
                z.writestr("report.json", json.dumps(data, indent=2, allow_nan=False))
                z.writestr(
                    "metrics.csv", "\ufeff" + csv_text(table_rows(data, snapshot))
                )
                z.writestr("review_state.json", json.dumps(snapshot, indent=2))
                z.writestr(
                    "review_state.csv",
                    "\ufeff"
                    + csv_text(
                        [
                            {
                                "stimulus_id": s["stimulus_id"],
                                "pair_id": s["pair_id"],
                                **snapshot["decisions"].get(
                                    s["stimulus_id"],
                                    {
                                        "status": "Unreviewed",
                                        "note": "",
                                        "reviewer": "",
                                        "revision": 0,
                                        "updated_at": "",
                                    },
                                ),
                            }
                            for s in data["stimuli"]
                        ]
                    ),
                )
                z.writestr(
                    "manifest.json",
                    json.dumps(
                        data["normalization_manifest"], indent=2, allow_nan=False
                    ),
                )
                z.writestr(
                    "README.txt",
                    "Read-only review snapshot. Start a local static server in this directory and open index.html.\n"
                    "Decisions, history and diagnostics are preserved; edits require the live SHINE review server.\n"
                    + (
                        "Images included.\n"
                        if include_images
                        else "Metadata only: image views are unavailable.\n"
                    ),
                )
                for p in (Path(__file__).parent / "assets").iterdir():
                    if p.is_file():
                        z.write(p, p.name)
                if include_images:
                    for s in data["stimuli"]:
                        for k in ("before_image", "after_image", "thumbnail"):
                            p = contained(self.root, s[k])
                            if digest(p.read_bytes()) != s["asset_sha256"][k]:
                                raise ValueError("Review image changed since analysis")
                            z.write(p, s[k])
            # Hard-link publication is atomic and refuses an existing destination.
            os.link(temporary, destination)
        finally:
            Path(temporary).unlink(missing_ok=True)
        return destination


def open_report(root, verify_assets=False):
    root = Path(root).resolve(strict=True)
    data = json.loads((root / "report.json").read_text(encoding="utf-8"))
    if data.get("schema_version") != SCHEMA or not data.get("stimuli"):
        raise ValueError("Unsupported or empty review report")
    ids = [r["stimulus_id"] for r in data["stimuli"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate stimulus ID")
    for row in data["stimuli"]:
        for key in ("before_image", "after_image", "thumbnail"):
            path = contained(root, row[key])
            if verify_assets and digest(path.read_bytes()) != row["asset_sha256"][key]:
                raise ValueError("Review image changed since analysis")
    return Report(root, data)


def _verify(rgb, record, actual):
    for key in ("file_sha256", "pixel_sha256"):
        if record.get(key) != actual[key]:
            raise ValueError(
                f"{key} mismatch for {record.get('name', record.get('filename'))}"
            )
    if record.get("dimensions") != [rgb.shape[1], rgb.shape[0]]:
        raise ValueError("Manifest dimensions do not match decoded image")


def _targets(rows, config, native):
    for name in rows[0]["channels"]:
        pres = [s["channels"][name]["pre"] for s in rows]
        hist = None
        if config["iterations"] != 1:
            mean = sd = None
            provenance = "unavailable: repeated-stage targets were not recorded"
        elif config["mode"] == 1:
            mean = float(np.mean([s["mean"] for s in pres]))
            sd = float(np.mean([s["sample_sd"] for s in pres]))
            provenance = (
                "derived: equal-image mean of input working-channel mean/sample SD"
            )
        elif native or len({(r["width"], r["height"]) for r in rows}) != 1:
            mean = sd = None
            provenance = "unavailable: histogram target requires supported equal-shape batch semantics"
        else:
            requested = matlab_round(
                np.mean([s["histogram"] for s in pres], axis=0)
            ).astype(np.int64)
            size = rows[0]["width"] * rows[0]["height"]
            # Count nearest-index selections analytically in strips. No random matching/replay.
            cumulative = requested.cumsum()
            hist = np.zeros(256, dtype=np.int64)
            for start in range(0, size, 65536):
                index = np.arange(start, min(start + 65536, size), dtype=float)
                pos = (
                    np.ones_like(index)
                    if size == 1
                    else 1 + index * ((requested.sum() - 1) / (size - 1))
                )
                if start + len(index) == size:
                    pos[-1] = requested.sum() if size > 1 else 1
                selected = np.clip(
                    matlab_round(pos).astype(np.int64) - 1, 0, requested.sum() - 1
                )
                hist += np.bincount(
                    np.searchsorted(cumulative, selected, side="right"), minlength=256
                )
            stats = diagnostics.histogram_stats(hist)
            mean, sd = stats["mean"], stats["sample_sd"]
            provenance = "derived: rounded average input histogram, SHINE target-list rank resampling"
        for row in rows:
            c = row["channels"][name]
            c.update(
                target_mean=mean,
                target_sample_sd=sd,
                target_provenance=provenance,
                target_histogram=None if hist is None else hist.tolist(),
                post_target_delta_mean=None
                if mean is None
                else c["post_saved"]["mean"] - mean,
                post_target_delta_sample_sd=None
                if sd is None
                else c["post_saved"]["sample_sd"] - sd,
                post_target_histogram_total_variation=None
                if hist is None
                else diagnostics.total_variation(c["post_saved"]["histogram"], hist),
            )


def compare_batch(inputs, outputs, *, manifest, review_dir, progress=None):
    """Import a completed batch (or native mode-1 run); never normalize images.

    inputs/outputs are explicit directory roots; manifest is a JSON path.
    Existing review projects are never overwritten. Each pair must align,
    but different pairs may have different native sizes.
    """
    source, output = (
        Path(inputs).resolve(strict=True),
        Path(outputs).resolve(strict=True),
    )
    destination = Path(review_dir).absolute()
    if destination.exists():
        raise FileExistsError(destination)
    if any(
        destination.resolve().is_relative_to(p)
        or p.is_relative_to(destination.resolve())
        for p in (source, output)
    ):
        raise ValueError("Review project must be separate from source/output trees")
    raw = Path(manifest).read_bytes()
    m = json.loads(raw)
    config = m.get("pipeline", {})
    if (
        m.get("schema_version") != 1
        or type(config.get("mode")) is not int
        or config["mode"] not in (1, 2)
    ):
        raise ValueError(
            "Phase 1 supports completed schema-1 mode 1 or 2 manifests only"
        )
    if type(config.get("iterations")) is not int or config["iterations"] < 1:
        raise ValueError("Invalid iteration count")
    if str(config.get("colorspace", "")).lower() not in ("rgb", "hsv", "lab", "cielab"):
        raise ValueError("Invalid colorspace")
    if m.get("workflow") not in (None, "native_dimension_CIELab_luminance_batch"):
        raise ValueError("Unsupported manifest workflow")
    native = m.get("workflow") == "native_dimension_CIELab_luminance_batch"
    if native and (
        config["mode"] != 1 or config["colorspace"].lower() not in ("lab", "cielab")
    ):
        raise ValueError("Unsupported native manifest configuration")
    ins, outs = m.get("inputs", []), m.get("outputs", [])
    if (
        len(ins) < 2
        or len(ins) != len(outs)
        or m.get("group", {}).get("count") != len(ins)
    ):
        raise ValueError("Incomplete group manifest")
    input_names = [r["name"] for r in ins]
    output_names = [r["filename"] for r in outs]
    if len(set(n.casefold() for n in input_names)) != len(ins) or len(
        set(n.casefold() for n in output_names)
    ) != len(outs):
        raise ValueError("Duplicate input/output names")
    if not native and m["group"].get("ordered_input_names") != input_names:
        raise ValueError("Manifest group ordering mismatch")
    by_source = {
        r.get("source_name", str(Path(r["filename"]).with_suffix(""))): r for r in outs
    }
    if len(by_source) != len(outs):
        raise ValueError("Ambiguous source/output mapping")
    pairs = []
    for record in ins:
        key = record["name"] if native else str(Path(record["name"]).with_suffix(""))
        if key not in by_source:
            raise ValueError("Unpaired source/output")
        pairs.append((record, by_source[key]))
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".shine-review-", dir=destination.parent))
    (stage / "images").mkdir()
    (stage / "thumbs").mkdir()
    run_id = digest(raw)
    rows = []
    try:
        for index, (a, b) in enumerate(pairs):
            before, ma = io._read_rgb(contained(source, a["name"]))
            after, mb = io._read_rgb(contained(output, b["filename"]))
            _verify(before, a, ma)
            _verify(after, b, mb)
            metrics = diagnostics.compare_pair(before, after, config["colorspace"])
            sid = digest(a["name"].encode())[:24]
            row = dict(
                stimulus_id=sid,
                pair_id=digest(canonical([a["file_sha256"], b["file_sha256"], run_id])),
                run_id=run_id,
                input_path=a["name"],
                output_path=b["filename"],
                input_sha256=a["file_sha256"],
                output_sha256=b["file_sha256"],
                width=before.shape[1],
                height=before.shape[0],
                **metrics,
                before_image=f"images/{sid}-before.png",
                after_image=f"images/{sid}-after.png",
                thumbnail=f"thumbs/{sid}.png",
                gamut_clip_fraction=None,
                gamut_clip_provenance="unavailable: not recorded; cannot infer from saved PNG",
            )
            if native:
                for key, target in [
                    ("rgb_out_of_gamut_pixel_fraction", "gamut_clip_fraction"),
                    ("working_L_clipped_fraction", "working_L_clip_fraction"),
                ]:
                    value = b.get(key)
                    if value is not None:
                        if (
                            not isinstance(value, (int, float))
                            or not np.isfinite(value)
                            or not 0 <= value <= 1
                        ):
                            raise ValueError("Invalid recorded fraction")
                        row[target] = value
                if row["gamut_clip_fraction"] is not None:
                    row["gamut_clip_provenance"] = (
                        "recorded: native-run manifest; pre-quantization RGB pixel fraction"
                    )
                values = b.get("working_L_after", {})
                if values:
                    c = row["channels"]["L"]
                    for key in ("mean", "sample_sd"):
                        value = values[key]
                        if not isinstance(value, (int, float)) or not np.isfinite(
                            value
                        ):
                            raise ValueError("Invalid recorded intermediate statistic")
                        c["recorded_intermediate_" + key] = value
                        c["post_minus_recorded_" + key] = c["post_saved"][key] - value
            io.save_rgb(before, stage / row["before_image"])
            io.save_rgb(after, stage / row["after_image"])
            thumb = Image.fromarray(after)
            thumb.thumbnail((320, 240))
            thumb.save(stage / row["thumbnail"])
            row["asset_sha256"] = {
                key: digest((stage / row[key]).read_bytes())
                for key in ("before_image", "after_image", "thumbnail")
            }
            rows.append(row)
            if progress:
                progress(index + 1, len(pairs))
        _targets(rows, config, native)
        summary = {}
        for channel in rows[0]["channels"]:
            values = [r["channels"][channel] for r in rows]
            summary[channel] = {
                side: dict(
                    mean_of_image_means=float(
                        np.mean([v[side]["mean"] for v in values])
                    ),
                    mean_of_image_sample_sds=float(
                        np.mean([v[side]["sample_sd"] for v in values])
                    ),
                    average_probability_histogram=np.mean(
                        [
                            np.array(v[side]["histogram"]) / sum(v[side]["histogram"])
                            for v in values
                        ],
                        axis=0,
                    ).tolist(),
                )
                for side in ("pre", "post_saved")
            }
        # Percentile is descriptive rank, with ties sharing the upper rank.
        scores = sorted(r["rgb_rmse"] for r in rows)
        for row in rows:
            row["rgb_rmse_percentile"] = (
                100
                * int(np.searchsorted(scores, row["rgb_rmse"], side="right"))
                / len(rows)
            )
        data = dict(
            schema_version=SCHEMA,
            project_id=digest(
                canonical([run_id, [(r["stimulus_id"], r["pair_id"]) for r in rows]])
            ),
            created_at=now(),
            metric_version=1,
            software=_software(),
            pipeline=config,
            normalization_manifest=m,
            manifest_sha256=run_id,
            stimuli=rows,
            summary=summary,
            domains={
                "L": "SHINE working L, uint8 0..255 (L* × 2.55, quantized)",
                "V": "SHINE working HSV V, uint8 0..255",
                "RGB": "Stored RGB uint8 codes",
            },
            policies={
                "post": "re-extracted from saved RGB output",
                "sd": "sample SD, ddof=1; singleton=0",
                "histogram_distance": "total variation of normalized 256-bin histograms, 0..1",
                "summary_weighting": "equal image weight; never pooled pixel weight",
                "display": "untagged PNG previews from verified decoded RGB; no ICC/gamma conversion",
                "ssim": "not implemented in Phase 1",
                "quality": "metrics describe changes, not scientific acceptability",
                "backlog": [
                    "spectral diagnostics",
                    "metadata joins",
                    "cross-run comparisons",
                ],
            },
        )
        write_json(stage / "report.json", data)
        for p in (Path(__file__).parent / "assets").iterdir():
            if p.is_file():
                shutil.copyfile(p, stage / p.name)
        (stage / "metrics.csv").write_text(
            csv_text(table_rows(data)), encoding="utf-8-sig", newline=""
        )
        if destination.exists():
            raise FileExistsError(destination)
        os.rename(stage, destination)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    report = Report(destination, data)
    from .state import ReviewState

    ReviewState(report)
    return report
