"""PNG/JPEG decoding and exact RGB uint8 PNG output. No color management.

EXIF orientation is applied to pixels. Alpha, transparency, high-bit-depth
data, unsupported color modes and multiple frames are rejected explicitly.
"""
from io import BytesIO
import hashlib
import os
from pathlib import Path
import tempfile
import time

import numpy as np
from PIL import Image, ImageOps

INPUT_SUFFIXES = frozenset({'.png', '.jpg', '.jpeg'})


def _rgb_array(image):
    if not isinstance(image, np.ndarray) or image.dtype != np.uint8:
        raise TypeError('image must be a uint8 NumPy array')
    if image.ndim != 3 or image.shape[2] != 3 or min(image.shape[:2]) < 1:
        raise ValueError('image must have nonempty shape (H,W,3)')
    return image


def pixel_sha256(image):
    """SHA-256 of RGB uint8 bytes in C order (H,W,3); record shape separately."""
    return hashlib.sha256(_rgb_array(image).tobytes(order='C')).hexdigest()


def _read_rgb(path):
    path = Path(path)
    if path.suffix.lower() not in INPUT_SUFFIXES:
        raise ValueError(f'Unsupported input extension: {path.name}; use PNG or JPEG')
    data = path.read_bytes()  # Hash and decode the same file snapshot.
    png = data.startswith(b'\x89PNG\r\n\x1a\n')
    if png and len(data) >= 29 and data[12:16] == b'IHDR' and data[24] > 8:
        raise ValueError(f'High-bit-depth PNG is not supported: {path.name}')
    with Image.open(BytesIO(data), formats=['PNG', 'JPEG']) as source:
        expected = 'PNG' if path.suffix.lower() == '.png' else 'JPEG'
        if source.format != expected:
            raise ValueError(f'File extension does not match decoded format: {path.name}')
        if getattr(source, 'n_frames', 1) != 1:
            raise ValueError(f'Multiple-frame images are not supported: {path.name}')
        if ('A' in source.getbands() or 'transparency' in source.info or
                (source.palette is not None and source.palette.mode == 'RGBA')):
            raise ValueError(f'Alpha/transparency is not supported: {path.name}')
        if source.mode not in ('RGB', 'L', '1', 'P') or getattr(source, 'bits', 8) > 8:
            raise ValueError(f'Unsupported image mode or bit depth: {source.mode} ({path.name})')
        orientation = source.getexif().get(274, 1)
        if not isinstance(orientation, int) or orientation not in range(1, 9):
            raise ValueError(f'Invalid EXIF orientation: {path.name}')
        metadata = dict(name=path.name, size_bytes=len(data),
                        file_sha256=hashlib.sha256(data).hexdigest(),
                        format=source.format, source_mode=source.mode,
                        stored_dimensions=list(source.size), exif_orientation=orientation,
                        orientation_applied=orientation != 1,
                        icc_profile_present=bool(source.info.get('icc_profile')),
                        gamma_present='gamma' in source.info)
        # ImageCms is deliberately not used. RGB values, L channel replication,
        # and palette lookup do not apply ICC/gamma transformations.
        oriented = ImageOps.exif_transpose(source)
        rgb = np.array(oriented.convert('RGB'), dtype=np.uint8, copy=True)
    metadata.update(dimensions=[rgb.shape[1], rgb.shape[0]],
                    pixel_sha256=pixel_sha256(rgb))
    return rgb, metadata


def load_rgb(path):
    """Load a supported single-frame PNG/JPEG as oriented RGB uint8 (H,W,3).

    Grayscale is replicated and opaque palette entries are looked up exactly.
    Stored color values are preserved; ICC/gamma metadata is not interpreted.
    """
    return _read_rgb(path)[0]


def _destination(path, overwrite):
    if not isinstance(overwrite, bool):
        raise TypeError('overwrite must be a bool')
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError(f'Destination must be a regular file, not a link/directory: {path.name}')
    if path.exists() and not overwrite:
        raise FileExistsError(f'Destination already exists: {path.name}')


def _publish_file(staged, destination, overwrite):
    if overwrite:
        os.replace(staged, destination)
    else:
        # Atomic no-clobber publication on supported filesystems (NTFS tested).
        # If hard links are unavailable, fail rather than use an unsafe fallback.
        os.link(staged, destination)


def _retry_sharing_violation(operation):
    """Bounded cleanup retry for transient Windows sharing/lock violations."""
    for delay in (0.05, 0.1, 0.2, 0.4, 0.8, 1.6, None):
        try:
            return operation()
        except PermissionError as error:
            if getattr(error, 'winerror', None) not in (32, 33) or delay is None:
                raise
            time.sleep(delay)


def _write_png(image, path):
    # A fresh image has no source ICC, gamma, EXIF, XMP or other metadata.
    Image.fromarray(_rgb_array(image)).save(path, format='PNG')


def save_rgb(image, path, *, overwrite=False):
    """Save exact RGB uint8 pixels as PNG, verify them, then publish atomically.

    The parent directory must exist. Existing files are protected by default.
    No source metadata is copied. Returns the destination Path.
    """
    _rgb_array(image)
    path = Path(path)
    if path.suffix.lower() != '.png':
        raise ValueError('Output must use .png; JPEG output is not supported')
    _destination(path, overwrite)
    fd, name = tempfile.mkstemp(prefix='.shine-png-', suffix='.png', dir=path.parent)
    os.close(fd)
    staged = Path(name)
    try:
        _write_png(image, staged)
        if not np.array_equal(load_rgb(staged), image):
            raise OSError('PNG verification failed before publication')
        _destination(path, overwrite)
        _publish_file(staged, path, overwrite)
    finally:
        _retry_sharing_violation(lambda: staged.unlink(missing_ok=True))
    return path
