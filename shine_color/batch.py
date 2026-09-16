"""File-based normalization of ONE image group through pipeline.run.

PNG outputs are staged and verified before publication. A manifest published
last marks success. Caught publication failures roll back; process/power loss
requires manual inspection of the retained lock/staging directory.
"""
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile

import numpy as np
import PIL
from PIL import features

from . import __version__, io, pipeline

_MANIFEST = 'manifest.json'
_LOCK = '.shine-color.lock'
_OPERATIONS = {'lum':'lum_match', 'hist':'hist_match', 'sf':'sf_match', 'spec':'spec_match'}


@dataclass(frozen=True)
class BatchResult:
    output_paths: tuple[Path, ...]
    manifest_path: Path
    manifest: dict


class BatchRecoveryError(RuntimeError):
    """Rollback failed; the named staging directory retains recovery copies."""


def _software():
    root = Path(__file__).resolve().parents[1]
    commit = dirty = None
    if (root/'.git').exists():
        try:
            commit = subprocess.run(['git','rev-parse','HEAD'], cwd=root, check=True,
                                    capture_output=True, text=True, timeout=5).stdout.strip()
            dirty = bool(subprocess.run(['git','status','--porcelain'], cwd=root, check=True,
                                       capture_output=True, text=True, timeout=5).stdout.strip())
        except (OSError, subprocess.SubprocessError):
            commit = dirty = None
    digest = hashlib.sha256()
    for path in sorted(Path(__file__).parent.glob('*.py')):
        digest.update(path.name.encode('utf-8')+b'\0'+path.read_bytes()+b'\0')
    return dict(project='shine-color', version=__version__, git_commit=commit,
                git_dirty=dirty, implementation_sha256=digest.hexdigest(),
                python=platform.python_version(), numpy=np.__version__, pillow=PIL.__version__,
                libjpeg=features.version_codec('jpg'), zlib=features.version_codec('zlib'))


def _resolve_inputs(inputs):
    if not isinstance(inputs, Sequence) or isinstance(inputs, (str, bytes, os.PathLike)):
        raise TypeError('inputs must be an ordered sequence of file paths')
    if len(inputs) < 2:
        raise ValueError('at least two input images are required')
    paths = [Path(p).expanduser().resolve(strict=True) for p in inputs]
    if any(not p.is_file() for p in paths):
        raise ValueError('each input must be a regular image file')
    identities = [(p.stat().st_dev, p.stat().st_ino) for p in paths]
    if len(set(identities)) != len(paths):
        raise ValueError('duplicate input files are not supported')
    names = [p.stem+'.png' for p in paths]
    if len({n.casefold() for n in names}) != len(names):
        raise ValueError('input stems collide in output filenames (case-insensitive)')
    return paths, names


def _preflight(output, names, inputs, overwrite):
    if not isinstance(overwrite, bool):
        raise TypeError('overwrite must be a bool')
    if output.is_symlink() or (output.exists() and not output.is_dir()):
        raise ValueError('output_dir must be a directory, not a file or symlink')
    existing = {p.name.casefold():p.name for p in output.iterdir()} if output.exists() else {}
    input_ids = {(p.stat().st_dev, p.stat().st_ino) for p in inputs}
    for name in [*names, _MANIFEST]:
        if name.casefold() in existing and existing[name.casefold()] != name:
            raise FileExistsError(f'Destination has a conflicting case variant: {name}')
        path = output/name
        io._destination(path, overwrite)
        if path.exists() and (path.stat().st_dev, path.stat().st_ino) in input_ids:
            raise ValueError('an output destination would overwrite an input file')


def _publish_batch(stage, output, names, overwrite):
    backup = stage/'backup'
    backup.mkdir()
    previous = {}
    # Copy all recoverable old files before touching any final destination.
    for name in [*names, _MANIFEST]:
        if overwrite and (output/name).exists():
            shutil.copyfile(output/name, backup/name)
            previous[name] = backup/name
    installed = []
    manifest_removed = False
    try:
        if _MANIFEST in previous:
            (output/_MANIFEST).unlink()
            manifest_removed = True
        for name in names:
            expected = hashlib.sha256((stage/name).read_bytes()).digest()
            io._publish_file(stage/name, output/name, overwrite)
            installed.append(name)
            if hashlib.sha256((output/name).read_bytes()).digest() != expected:
                raise OSError(f'Published file failed verification: {name}')
        io._publish_file(stage/_MANIFEST, output/_MANIFEST, overwrite)
    except BaseException as original:
        errors = []
        for name in reversed(installed):
            try:
                if name in previous: os.replace(previous[name], output/name)
                else: (output/name).unlink(missing_ok=True)
            except OSError as error:
                errors.append(error)
        # Restore an old success marker only after EVERY old output is restored.
        if manifest_removed and not errors:
            try: os.replace(previous[_MANIFEST], output/_MANIFEST)
            except OSError as error: errors.append(error)
        if errors:
            raise BatchRecoveryError(f'Rollback incomplete; retain lock and inspect recovery files at {stage}') from original
        raise


def process_files(inputs, output_dir, colorspace, mode, iterations=1, rescale_option=1, *, overwrite=False):
    """Normalize the ordered list as one group, save PNGs and manifest.json.

    All oriented RGB images must share dimensions. Caller order is preserved.
    Existing destinations fail preflight unless overwrite=True. Source files
    can never be destinations. Histogram modes remain stochastic and unseeded.
    Returns BatchResult with paths and the exact JSON-compatible manifest.
    """
    paths, names = _resolve_inputs(inputs)
    output = Path(output_dir).expanduser().absolute()
    decoded = [io._read_rgb(path) for path in paths]
    images = [item[0] for item in decoded]
    if any(image.shape != images[0].shape for image in images):
        raise ValueError('all oriented input images must have the same dimensions')
    _preflight(output, names, paths, overwrite)
    if (output/_LOCK).exists():
        raise FileExistsError('output directory is locked; inspect any interrupted batch first')
    started = datetime.now(timezone.utc).isoformat()
    software = _software()
    # The sole scientific call: never normalize files independently.
    arrays = pipeline.run(images, colorspace, mode, iterations, rescale_option)
    if len(arrays) != len(images) or any(io._rgb_array(a).shape != images[0].shape for a in arrays):
        raise ValueError('pipeline returned an invalid output group')
    operations = [_OPERATIONS[op] for op in pipeline._MODES[mode]]
    output.mkdir(parents=True, exist_ok=True)
    lock = output/_LOCK
    lock.mkdir()  # Exclusive ownership among cooperating batch calls.
    stage = None
    retain = False
    try:
        _preflight(output, names, paths, overwrite)
        stage = Path(tempfile.mkdtemp(prefix='.shine-stage-', dir=output))
        records = []
        for name, array in zip(names, arrays):
            path = stage/name
            io.save_rgb(array, path)
            records.append(dict(filename=name, dimensions=[array.shape[1], array.shape[0]],
                                size_bytes=path.stat().st_size,
                                file_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                                pixel_sha256=io.pixel_sha256(array)))
        manifest = dict(schema_version=1, software=software,
            pipeline=dict(colorspace={'rgb':'RGB','hsv':'HSV','lab':'CIELab','cielab':'CIELab'}[colorspace.lower()],
                          mode=int(mode), ordered_mode_operations=operations,
                          iterations=int(iterations), rescale_option=int(rescale_option)),
            group=dict(count=len(paths), ordering='provided_sequence',
                       ordered_input_names=[p.name for p in paths]),
            processing_started_utc=started, processing_completed_utc=datetime.now(timezone.utc).isoformat(),
            overwrite=overwrite,
            histogram_tie_breaking='stochastic_unseeded' if 'hist' in pipeline._MODES[mode] else 'not_applicable',
            io_policy=dict(input_formats=['PNG','JPEG'], output_format='PNG',
                           alpha='reject', high_bit_depth='reject', grayscale='replicate',
                           palette='opaque_RGB_lookup', orientation='apply_EXIF_to_pixels',
                           color_management='stored_codes_no_ICC_or_gamma_transform', output_metadata='none'),
            hashing=dict(file='SHA-256 of exact file bytes',
                         pixels='SHA-256 of uint8 RGB buffer in C order (H,W,3); dimensions stored as [width,height]'),
            inputs=[item[1] for item in decoded], outputs=records)
        (stage/_MANIFEST).write_text(json.dumps(manifest, indent=2, allow_nan=False)+'\n', encoding='utf-8')
        _publish_batch(stage, output, names, overwrite)
        return BatchResult(tuple(output/n for n in names), output/_MANIFEST, manifest)
    except BatchRecoveryError:
        retain = True
        raise
    finally:
        if not retain:
            if stage is not None:
                # Delete only the fresh staging directory inside the named output.
                if stage.resolve().parent != output.resolve() or not stage.name.startswith('.shine-stage-'):
                    raise RuntimeError('Refusing cleanup outside the output directory')
                io._retry_sharing_violation(lambda: shutil.rmtree(stage))
            # If cleanup fails persistently, leave the lock for manual inspection.
            io._retry_sharing_violation(lock.rmdir)


def process_directory(input_dir, output_dir, colorspace, mode, iterations=1, rescale_option=1, *, overwrite=False):
    """Process supported top-level regular files as one group, non-recursively.

    Order is (filename.casefold(), filename), using Python Unicode ordering.
    Unsupported extensions, symlinks and subdirectories are ignored. Supported
    extensions with invalid content raise an error rather than being skipped.
    Input and output directories must differ; nested output directories are safe.
    """
    source = Path(input_dir).expanduser().resolve(strict=True)
    if not source.is_dir(): raise ValueError('input_dir must be a directory')
    if source == Path(output_dir).expanduser().resolve():
        raise ValueError('input and output directories must differ')
    paths = sorted((p for p in source.iterdir() if not p.is_symlink() and p.is_file()
                    and p.suffix.lower() in io.INPUT_SUFFIXES), key=lambda p:(p.name.casefold(),p.name))
    return process_files(paths, output_dir, colorspace, mode, iterations, rescale_option, overwrite=overwrite)
