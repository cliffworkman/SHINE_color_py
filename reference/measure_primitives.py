"""Measure first; test bounds are reviewed separately, never auto-increased."""
from pathlib import Path
import json
import platform

import numpy as np
import scipy
from scipy.io import loadmat

from shine_color.histogram import average_histogram, histogram_to_value_list, hist_match
from shine_color.luminance import lum_match
from shine_color.numeric import imhist256, sample_std, to_uint8
from shine_color.rescale import rescale
from shine_color.spatial_frequency import sf_match, _decompose
from shine_color.spectrum import spec_match

FIXTURES = Path(__file__).resolve().parents[1] / 'tests/reference/fixtures'


def cells(value):
    return list(value.ravel())


def difference(actual, expected):
    a, b = np.asarray(actual), np.asarray(expected)
    if a.shape != b.shape:
        raise ValueError(f'Shape mismatch: {a.shape} vs {b.shape}')
    d = np.abs(a.astype(complex) - b.astype(complex))
    nonzero = np.abs(b) > 0
    return dict(max_abs=float(d.max(initial=0)), mean_abs=float(d.mean()),
                p95_abs=float(np.quantile(d, .95)),
                max_relative_nonzero=float((d[nonzero]/np.abs(b[nonzero])).max(initial=0)),
                unequal_count=int(np.count_nonzero(d)), size=int(d.size))


def measurements():
    result = {}
    numeric = loadmat(FIXTURES/'numeric.mat')
    result['uint8'] = difference(to_uint8(numeric['cast_input']), numeric['cast_output'])
    for path in sorted(FIXTURES.glob('primitives_*.mat')):
        f = loadmat(path)
        inputs = cells(f['inputs'])
        checks = dict(rescale1=rescale(inputs,1), rescale2=rescale(inputs,2),
                      luminance=lum_match(inputs),
                      constant_luminance=lum_match(cells(f['constant_inputs'])),
                      input_histograms=[imhist256(a)[:,None] for a in inputs])
        histograms = hist_match(inputs, rng=np.random.default_rng(183))
        checks['output_histograms'] = [imhist256(a)[:,None] for a in histograms]
        for name, actual in checks.items():
            for k,(a,b) in enumerate(zip(actual,cells(f[name]))):
                result[f'{path.stem}/{name}/{k}'] = difference(a,b)
        for name, actual in [('means',[a.mean() for a in inputs]),
                             ('sample_sds',[sample_std(a) for a in inputs]),
                             ('histogram_means',[a.mean() for a in histograms]),
                             ('histogram_sds',[sample_std(a) for a in histograms]),
                             ('target_histogram',average_histogram(inputs)),
                             ('target_values',histogram_to_value_list(average_histogram(inputs)))]:
            result[f'{path.stem}/{name}'] = difference(np.asarray(actual).ravel(),f[name].ravel())
        amps = []
        for k,a in enumerate(inputs):
            phase, amp = _decompose(a); amps.append(amp)
            result[f'{path.stem}/amplitudes/{k}'] = difference(amp,cells(f['amplitudes'])[k])
            # Compare unit phase vectors, avoiding equivalent +/-pi branch cuts.
            result[f'{path.stem}/phase_unit/{k}'] = difference(np.exp(1j*phase),np.exp(1j*cells(f['phases'])[k]))
        result[f'{path.stem}/target_amplitude'] = difference(np.mean(amps,axis=0),f['target_amplitude'])
        for name, func in [('sf_outputs',sf_match),('spec_outputs',spec_match)]:
            for option,expected in enumerate(cells(f[name])):
                for k,(a,b) in enumerate(zip(func(inputs,option),cells(expected))):
                    result[f'{path.stem}/{name}/{option}/{k}'] = difference(a,b)
    return dict(environment=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__), comparisons=result)


if __name__ == '__main__':
    report = measurements()
    (FIXTURES/'primitive_differences.json').write_text(json.dumps(report,indent=2)+'\n')
    for key,val in report['comparisons'].items():
        if val['max_abs']:
            print(key, val)
