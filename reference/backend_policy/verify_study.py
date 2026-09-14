"""Audit recorded evidence independently; these checks never set output tolerances."""
import csv
import datetime
import hashlib
import json
import platform
import re
from collections import Counter
from pathlib import Path

import numpy as np
import scipy
import PIL
from PIL import Image
from scipy.io import loadmat
from reference.compare_fft_backends import pyfftw
from reference.measure_primitives import cells
from .build_corpus import ROOT, DATA
from .screen_conditioning import CACHE


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    manifest = json.loads((ROOT/'corpus_manifest.json').read_text())
    conditioning = json.loads((ROOT/'conditioning.json').read_text())
    result = json.loads((ROOT/'results.json').read_text())
    assert sha(ROOT/'CRITERIA.md') == manifest['criteria_sha256'] == conditioning['criteria_sha256']
    assert sha(ROOT/'conditioning.json') == result['conditioning_sha256']
    assert result['input_sha256'] == manifest['input_sha256']
    assert len(manifest['groups']) == len(conditioning['groups']) == 9
    for name, expected in manifest['input_sha256'].items():
        assert sha(DATA/name) == expected
    for name, expected in result['reference_output_sha256'].items():
        assert sha(CACHE/name) == expected
    for group in manifest['groups']:
        name = group['name']
        screen = next(g for g in conditioning['groups'] if g['name'] == name)
        assert sha(CACHE/(name+'_spectra.mat')) == screen['spectra_sha256']
        arrays = cells(loadmat(DATA/(name+'_inputs.mat'))['inputs'])
        assert len(arrays) == 3
        for k, a in enumerate(arrays):
            assert a.dtype == np.uint8 and list(a.shape) == group['shape']
            if group['kind'] == 'synthetic_candidate':
                with Image.open(DATA/f'{name}_{k+1}.png') as im:
                    assert np.array_equal(a, np.array(im))
            else:
                source = group['sources'][k]
                assert sha(Path(source['path'])) == source['sha256']
                with Image.open(source['path']) as im:
                    assert np.array_equal(a, np.array(im)[::group['stride'], ::group['stride'], 1])
    with (ROOT/'output_comparisons.csv').open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == len(result['comparisons']) == 324
    for csv_row, row in zip(rows, result['comparisons']):
        for key in ('fixture', 'kind', 'runtime', 'operation'):
            assert csv_row[key] == row[key]
        for key in ('option', 'source', 'elements', 'unequal', 'max_abs', 'mean_abs'):
            assert float(csv_row[key]) == row[key]
        assert json.loads(csv_row['nonzero_distribution']) == row['nonzero_distribution']
    for key, aggregate in result['summary'].items():
        runtime, kind = key.split('/')
        subset = [r for r in rows if r['runtime'] == runtime and r['kind'] == kind]
        histogram = Counter()
        for row in subset:
            histogram.update(json.loads(row['nonzero_distribution']))
        pixels = sum(int(r['elements']) for r in subset)
        total_error = sum(int(v)*count for v, count in histogram.items())
        assert aggregate['images'] == len(subset)
        assert aggregate['exact_images'] == sum(int(r['unequal']) == 0 for r in subset)
        assert aggregate['pixels'] == pixels
        assert aggregate['max_abs'] == max(map(int, histogram), default=0)
        assert aggregate['nonzero_distribution'] == dict(histogram)
        assert aggregate['pixel_weighted_mae'] == total_error/pixels
    audit = dict(checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        checks='source hashes and channel extraction, PNG/MAT equality, shapes/dtypes, criteria/spectra/output hashes, CSV/JSON agreement and independent aggregates',
        passed=True, groups=9, comparisons=324,
        environment=dict(python=platform.python_version(), platform=platform.platform(),
            numpy=np.__version__, scipy=scipy.__version__, pillow=PIL.__version__,
            pyfftw=pyfftw.__version__, fftw_reported=pyfftw.fftw_version,
            fftw_binary_markers=sorted({m.decode() for p in Path(pyfftw.__file__).parent.glob('*.dll')
                for m in re.findall(rb'fftw-3\.[0-9]+\.[0-9]+', p.read_bytes())})),
        python_fftw_configuration=dict(transform='c2c', transpose=True, threads=1,
            planner='FFTW_ESTIMATE', wisdom='forgotten before each backend/group'),
        results_sha256=sha(ROOT/'results.json'))
    (ROOT/'audit.json').write_text(json.dumps(audit, indent=2)+'\n', newline='\n')
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    verify()
