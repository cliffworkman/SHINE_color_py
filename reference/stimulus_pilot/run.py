"""Run and report the bounded architectural-image pilot.

This module is research-facing orchestration around ``shine_color.batch``.
It deliberately does not add a second normalization path or modify the
validated library algorithms.
"""
from __future__ import annotations

from contextlib import contextmanager
import csv
import hashlib
import html
import json
from pathlib import Path
import shutil
import tempfile

import numpy as np

from shine_color import batch, color, io, pipeline
from .metrics import (array_hash, cast_metrics, channel_metrics, change, conditioning,
                      dispersion, spectral_group, working_channels)
from .selection import inventory, select_sample


EXPLORATORY_CONFIGS = (
    dict(label="hsv_mode1_lum", colorspace="HSV", mode=1, iterations=1, rescale_option=1,
         rationale="working V mean/sample-SD matching"),
    dict(label="hsv_mode3_sf", colorspace="HSV", mode=3, iterations=1, rescale_option=1,
         rationale="working V radial spatial-frequency matching"),
    dict(label="hsv_mode6_hist_spec", colorspace="HSV", mode=6, iterations=1, rescale_option=1,
         rationale="histogram then full-spectrum ordering"),
    dict(label="hsv_mode8_spec_hist", colorspace="HSV", mode=8, iterations=1, rescale_option=1,
         rationale="full-spectrum then histogram ordering"),
)


def _json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
                    encoding="utf-8")


def _safe_output(source, output):
    source = Path(source).resolve()
    output = Path(output).resolve()
    if output == source or source in output.parents:
        raise ValueError("pilot output must be outside the source directory")
    output.mkdir(parents=True, exist_ok=True)
    return source, output


def prepare(source, output, *, limit=24):
    """Inventory all candidates and freeze a common-shape pilot manifest."""
    source, output = _safe_output(source, output)
    inv = inventory(source)
    _json(output / "inventory.json", inv)
    valid = [r for r in inv["rows"] if r["valid"]]
    if not valid:
        raise ValueError("the candidate directory has no readable images")
    dimensions = {}
    for row in valid:
        dimensions.setdefault(tuple(row["dimensions"]), []).append(row)
    # Stable tie break: highest count, then width/height lexical order.
    required = max(dimensions, key=lambda d: (len(dimensions[d]), tuple(-x for x in d)))
    eligible = [r for r in valid if tuple(r["dimensions"]) == required]
    chosen, rule = select_sample(eligible, limit=limit)
    # The sample function is intentionally output-independent; this is the
    # only place where the no-resize/common-shape batch constraint is applied.
    rule = dict(rule, eligible_dimensions=list(required), eligible_count=len(eligible),
                excluded_for_native_shape=inv["summary"]["candidate_files"] - len(eligible),
                selection_scope="largest native-dimension cohort; no resize/crop/upscale")
    manifest = dict(schema_version=1, source_directory=str(source), source_stage="final spatially preprocessed candidates (user supplied)",
                    source_count=inv["summary"]["candidate_files"], readable_count=inv["summary"]["readable"],
                    pilot_count=len(chosen), pilot_only_group=True,
                    grouping_note="one exploratory pilot group; does not establish final experimental grouping",
                    settings_status="exploratory; no authoritative SHINE settings were supplied",
                    selection_rule=rule, dimensions=list(required),
                    candidates=[{k: r[k] for k in ("relative_path", "file_sha256", "pixel_sha256", "dimensions",
                                                   "v_mean", "v_sample_sd", "v_entropy_bits", "v_low_power_fraction")}
                                for r in chosen],
                    configs=[dict(c) for c in EXPLORATORY_CONFIGS])
    manifest["manifest_sha256"] = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    _json(output / "pilot_manifest.json", manifest)
    return inv, manifest


@contextmanager
def _stage_capture(records, cast_records, config):
    """Capture actual primitive stage inputs/outputs while delegating originals."""
    original_process = pipeline._process_channel
    from shine_color import histogram, luminance, rescale, spatial_frequency, spectrum
    modules = [pipeline, histogram, luminance, rescale, spatial_frequency, spectrum]
    originals = {module: module.to_uint8 for module in modules if hasattr(module, "to_uint8")}
    active = {"stage": None}

    def captured(values, *, _module):
        marker = active["stage"]
        cast_records.append(dict(module=_module.__name__, operation=(marker["operation"] if marker else "terminal"),
                                 stage_index=(marker["stage_index"] if marker else None), metrics=cast_metrics(values)))
        return originals[_module](values)

    for module in originals:
        module.to_uint8 = lambda values, _module=module: captured(values, _module=_module)
    channel_counter = {"n": 0}

    def wrapped(images, mode, iterations, rescale_option, *, rng=None):
        channel = channel_counter["n"]
        channel_counter["n"] += 1
        current = list(images)
        for iteration in range(iterations):
            for stage_index, operation in enumerate(pipeline._MODES[mode]):
                before = [np.array(a, copy=True) for a in current]
                active["stage"] = {"operation": operation, "stage_index": stage_index + 1}
                # Keep the library's exact implementation and RNG behavior.
                current = original_process(
                    before,  # one full call would repeat operations; use primitive below
                    1 if operation == "lum" else ({"hist": 2, "sf": 3, "spec": 4}[operation]),
                    1, rescale_option, rng=rng)
                # The mode mapping above would execute a one-stage mode, which
                # is equivalent to the primitive and preserves the validated code.
                after = [np.array(a, copy=True) for a in current]
                records.append(dict(channel_index=channel, iteration=iteration + 1,
                                    stage_index=stage_index + 1, operation=operation,
                                    before=before, after=after))
                active["stage"] = None
        return current

    pipeline._process_channel = wrapped
    try:
        yield
    finally:
        pipeline._process_channel = original_process
        for module, original in originals.items():
            module.to_uint8 = original


def _stage_summary(stage, config):
    before, after = stage["before"], stage["after"]
    out = dict(channel_index=stage["channel_index"], iteration=stage["iteration"],
               stage_index=stage["stage_index"], operation=stage["operation"],
               mode=config["mode"], colorspace=config["colorspace"])
    out["before_sha256"] = [array_hash(a) for a in before]
    out["after_sha256"] = [array_hash(a) for a in after]
    out["before_dispersion"] = dispersion([channel_metrics(a) for a in before])
    out["after_dispersion"] = dispersion([channel_metrics(a) for a in after])
    if stage["operation"] in ("sf", "spec"):
        out["conditioning"] = [conditioning(a) for a in before]
        out["spectral_before"] = spectral_group(before)[0]
        out["spectral_after"] = spectral_group(after)[0]
    return out


def _working_summary(source_rgb, output_rgb, config):
    source = working_channels(source_rgb, config["colorspace"])
    final = working_channels(output_rgb, config["colorspace"])
    result = {}
    for key in source:
        b = channel_metrics(source[key]); a = channel_metrics(final[key])
        result[key] = dict(before=b, final=a)
        if key == "V" or key in ("R", "G", "B", "L"):
            result[key]["spectral_before"] = spectral_group([source[key]])[0]["images"][0]
            result[key]["spectral_final"] = spectral_group([final[key]])[0]["images"][0]
    result["rgb_change"] = change(source_rgb, output_rgb)
    return result


def run_config(source, output, manifest, config):
    source = Path(source); output = Path(output)
    paths = [source / r["relative_path"] for r in manifest["candidates"]]
    for path, frozen in zip(paths, manifest["candidates"]):
        if io._read_rgb(path)[1]["file_sha256"] != frozen["file_sha256"]:
            raise RuntimeError(f"source changed after manifest freeze: {path.name}")
    records = []
    cast_records = []
    destination = output / config["label"]
    with _stage_capture(records, cast_records, config):
        result = batch.process_files(paths, destination, config["colorspace"], config["mode"],
                                     config["iterations"], config["rescale_option"], overwrite=False)
    outputs = []
    for path in result.output_paths:
        outputs.append(io._read_rgb(path)[0])
    sources = [io._read_rgb(p)[0] for p in paths]
    image_rows = []
    for row, before, after in zip(manifest["candidates"], sources, outputs):
        image_rows.append(dict(image=row["relative_path"], source_sha256=row["file_sha256"],
                               output_sha256=hashlib.sha256((destination / (Path(row["relative_path"]).stem + ".png")).read_bytes()).hexdigest(),
                               metrics=_working_summary(before, after, config)))
    stage_rows = [_stage_summary(s, config) for s in records]
    for stage in stage_rows:
        stage["casts"] = [c for c in cast_records if c["stage_index"] == stage["stage_index"]
                          and c["operation"] == stage["operation"]]
    final_channels = {}
    for key in working_channels(outputs[0], config["colorspace"]):
        final_channels[key] = spectral_group(
            [working_channels(a, config["colorspace"])[key] for a in outputs])[0]
    return dict(config=config, output_directory=str(destination), manifest=result.manifest,
                images=image_rows, stages=stage_rows, final_spectral_group=final_channels,
                terminal_casts=[c for c in cast_records if c["operation"] == "terminal"])


def _csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def _report_html(output, manifest, results):
    cards = []
    for row in manifest["candidates"]:
        images = []
        for result in results:
            hit = next(x for x in result["images"] if x["image"] == row["relative_path"])
            change_row = hit["metrics"]["rgb_change"]
            dest = Path(result["output_directory"])
            rel = Path(dest.name) / (Path(row["relative_path"]).stem + ".png")
            images.append(f'<div class="arm"><b>{html.escape(result["config"]["label"])}</b>'
                          f'<img src="{html.escape(str(rel).replace(chr(92), "/"))}" loading="lazy">'
                          f'<small>changed {change_row["changed_scalar_percent"]:.2f}% · MAE {change_row["rgb_mae"]:.2f}</small></div>')
        cards.append('<article><h3>'+html.escape(row["relative_path"])+'</h3>'
                     '<div class="row"><div class="arm"><b>original</b>'
                     f'<img src="original/{html.escape(Path(row["relative_path"]).stem)}.png" loading="lazy"></div>'
                     + ''.join(images) + '</div></article>')
    body = ''.join(cards)
    return """<!doctype html><meta charset="utf-8"><title>SHINE architectural pilot</title>
<style>body{font:14px system-ui;margin:2rem;background:#f6f6f6;color:#222}article{background:white;padding:1rem;margin:1rem 0}h1{margin-bottom:.2rem}.row{display:flex;gap:1rem;flex-wrap:wrap}.arm{width:220px}.arm img{display:block;max-width:220px;max-height:180px;object-fit:contain;background:#ddd}.arm small{display:block;margin-top:.3rem}code{word-break:break-all}</style>
<h1>Architectural SHINE pilot</h1><p><b>Exploratory only.</b> One pilot-only group; no final experimental grouping or full-corpus generation. The sample is frozen from the largest native-dimension cohort; no resizing, cropping, or upscaling was performed.</p>
<p>Settings compared: HSV mode 1 (lum), mode 3 (sf), mode 6 (hist→spec), and mode 8 (spec→hist), one iteration, rescale option 1. Review the mode ordering effects visually alongside the quantitative artifacts.</p>
""" + body


def write_report(output, manifest, results):
    output = Path(output)
    original_dir = output / "original"
    original_dir.mkdir(exist_ok=True)
    image_rows = []
    stage_rows = []
    for result in results:
        stage_rows.extend({"config": result["config"]["label"], **row} for row in result["stages"])
        image_rows.extend({"config": result["config"]["label"], "image": row["image"],
                           "source_sha256": row["source_sha256"], "output_sha256": row["output_sha256"],
                           "rgb_change": json.dumps(row["metrics"]["rgb_change"], sort_keys=True)}
                          for row in result["images"])
    _json(output / "metrics_summary.json", dict(manifest=manifest, results=results))
    _csv(output / "metrics_per_image.csv", image_rows,
         ["config", "image", "source_sha256", "output_sha256", "rgb_change"])
    # Stage rows retain nested conditioning/dispersion JSON so no metric is lost.
    flat = []
    for row in stage_rows:
        flat.append({"config": row["config"], "channel_index": row["channel_index"],
                     "iteration": row["iteration"], "stage_index": row["stage_index"],
                     "operation": row["operation"], "conditioning": json.dumps(row.get("conditioning", [])),
                     "casts": json.dumps(row.get("casts", []), sort_keys=True),
                     "before_dispersion": json.dumps(row["before_dispersion"]),
                     "after_dispersion": json.dumps(row["after_dispersion"]),
                     "spectral_before": json.dumps(row.get("spectral_before", {})),
                     "spectral_after": json.dumps(row.get("spectral_after", {}))})
    _csv(output / "spectral_conditioning.csv", flat,
         ["config", "channel_index", "iteration", "stage_index", "operation", "conditioning", "casts",
          "before_dispersion", "after_dispersion", "spectral_before", "spectral_after"])
    # Copying originals into the ignored report artifact is for visual review;
    # source files themselves remain untouched and are never committed.
    for row in manifest["candidates"]:
        src = Path(manifest["source_directory"]) / row["relative_path"]
        original_path = original_dir / (Path(row["relative_path"]).stem + ".png")
        if not original_path.exists():
            io.save_rgb(io._read_rgb(src)[0], original_path, overwrite=False)
    (output / "pilot_report.html").write_text(_report_html(output, manifest, results), encoding="utf-8")


def run_pilot(source, output, *, limit=24):
    inv, manifest = prepare(source, output, limit=limit)
    results = [run_config(source, output, manifest, config) for config in EXPLORATORY_CONFIGS]
    write_report(output, manifest, results)
    return dict(inventory=inv, manifest=manifest, results=results)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("output")
    parser.add_argument("--limit", type=int, default=24)
    args = parser.parse_args()
    run_pilot(args.source, args.output, limit=args.limit)
