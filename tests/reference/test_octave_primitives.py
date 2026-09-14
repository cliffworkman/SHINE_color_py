"""Strict Octave parity and explicitly accepted FFT degeneracy conditions."""
from pathlib import Path
from contextlib import nullcontext
import json

import numpy as np
import pytest
from scipy.io import loadmat

from shine_color.histogram import average_histogram, histogram_to_value_list, hist_match, match_histogram
from shine_color.luminance import lum_match
from shine_color.numeric import imhist256, sample_std, to_uint8
from shine_color.rescale import rescale
from shine_color.spatial_frequency import sf_match, _decompose, _radial_bin_grid
from shine_color import spatial_frequency, spectrum
from shine_color.spectrum import spec_match

FIXTURES = Path(__file__).with_name('fixtures')
CASES = sorted(FIXTURES.glob('primitives_*.mat'))
# Observed max SD and amplitude differences: 2.842170943040401e-14.
# Exactly 128 float64 eps; no relative tolerance or hidden default added.
FLOAT_ABS = 128 * np.finfo(np.float64).eps


def cells(value):
    return list(value.ravel())


def assert_images(actual, expected):
    expected = cells(expected)
    assert len(actual) == len(expected)
    for a,b in zip(actual,expected):
        assert a.shape == b.shape
        assert a.dtype == b.dtype == np.uint8
        # Signed comparison also prevents uint8 wrap in pytest's error summary.
        np.testing.assert_array_equal(a.astype(np.int16),b.astype(np.int16))


@pytest.fixture(params=CASES, ids=lambda p:p.stem)
def fixture(request):
    return loadmat(request.param)


def test_saturating_cast():
    f = loadmat(FIXTURES/'numeric.mat')
    np.testing.assert_array_equal(to_uint8(f['cast_input']),f['cast_output'])


@pytest.mark.parametrize('option',[1,2])
def test_rescale(fixture,option):
    assert_images(rescale(cells(fixture['inputs']),option),fixture[f'rescale{option}'])


def test_luminance(fixture):
    inputs = cells(fixture['inputs'])
    assert_images(lum_match(inputs),fixture['luminance'])
    assert_images(lum_match(cells(fixture['constant_inputs'])),fixture['constant_luminance'])
    np.testing.assert_array_equal([a.mean() for a in inputs],fixture['means'].ravel())
    np.testing.assert_allclose([sample_std(a) for a in inputs],fixture['sample_sds'].ravel(),rtol=0,atol=FLOAT_ABS)


def test_histogram_invariants(fixture):
    inputs = cells(fixture['inputs'])
    for a,h in zip(inputs,cells(fixture['input_histograms'])):
        np.testing.assert_array_equal(imhist256(a),h.ravel())
    target = average_histogram(inputs)
    np.testing.assert_array_equal(target,fixture['target_histogram'].ravel())
    np.testing.assert_array_equal(histogram_to_value_list(target),fixture['target_values'].ravel())
    for seed in range(5):
        outputs = hist_match(inputs,rng=np.random.default_rng(seed))
        assert len(outputs) == len(inputs)
        for a,b,h in zip(inputs,outputs,cells(fixture['output_histograms'])):
            assert b.shape == a.shape and b.dtype == np.uint8
            np.testing.assert_array_equal(imhist256(b),h.ravel())
        np.testing.assert_array_equal([b.mean() for b in outputs],fixture['histogram_means'].ravel())
        np.testing.assert_allclose([sample_std(b) for b in outputs],fixture['histogram_sds'].ravel(),rtol=0,atol=FLOAT_ABS)


def test_fft_diagnostics(fixture):
    amplitudes = []
    for a,expected in zip(cells(fixture['inputs']),cells(fixture['amplitudes'])):
        _,amp = _decompose(a); amplitudes.append(amp)
        np.testing.assert_allclose(amp,expected,rtol=0,atol=FLOAT_ABS)
    np.testing.assert_allclose(np.mean(amplitudes,axis=0),fixture['target_amplitude'],rtol=0,atol=FLOAT_ABS)


DEGENERATE = {
    ('primitives_5x7', 'spec'): 'forward_phase',
    ('primitives_5x8', 'spec'): 'forward_phase',
    ('primitives_6x8', 'spec'): 'forward_phase',
    ('primitives_8x5', 'spec'): 'forward_phase',
    ('primitives_5x8', 'sf'): 'radial_energy',
    ('primitives_8x5', 'sf'): 'radial_energy',
}
FREQUENCY_CASES = [pytest.param(p, op, option,
    marks=[pytest.mark.octave_degenerate_spectrum] if (p.stem, op) in DEGENERATE else [],
    id=f'{p.stem}-{op}-{option}')
    for p in CASES for op in ('sf', 'spec') for option in (0, 1, 2)]


@pytest.mark.parametrize('path,op,option', FREQUENCY_CASES)
def test_frequency_outputs(path, op, option, monkeypatch):
    fixture = loadmat(path)
    inputs = cells(fixture['inputs'])
    module, operation = (spatial_frequency, sf_match) if op == 'sf' else (spectrum, spec_match)
    expected = cells(fixture[op+'_outputs'])[option]
    actual = operation(inputs, option)
    classification = DEGENERATE.get((path.stem, op))
    if classification is None:
        assert_images(actual, expected)
        return

    # Every formerly failing case is explicitly mapped above, never inferred
    # from whether its output happens to pass. Source 3 has mathematical zeros.
    source = inputs[2].astype(int)
    np.testing.assert_array_equal(source-source[:, :1]-source[:1, :]+source[0, 0], 0)
    phase, amplitude = _decompose(source)
    ref_amp = cells(fixture['amplitudes'])[2]
    ref_phase = cells(fixture['phases'])[2]
    threshold = 1e-10 * max(1., float(ref_amp.max()))
    low = (ref_amp <= threshold) | (amplitude <= threshold)
    target = fixture['target_amplitude']
    assert np.any(low)
    if classification == 'forward_phase':
        # A unit-vector separation >1 is a substantive phase disagreement,
        # not a relaxed floating-point comparison or a final pixel tolerance.
        promoted = low & (target > threshold)
        assert np.max(np.abs(np.exp(1j*phase[promoted])-np.exp(1j*ref_phase[promoted]))) > 1
    else:
        radial = _radial_bin_grid(*source.shape)
        sums = lambda a: np.bincount(radial.ravel(), weights=a.ravel())
        denominator, py_denominator, numerator = sums(ref_amp), sums(amplitude), sums(target)
        retained = np.arange(len(denominator)) <= np.floor(max(source.shape)/2)
        singular = retained & (denominator <= threshold) & (numerator > threshold)
        assert np.any(singular)
        assert np.any(denominator[singular] != py_denominator[singular])
        # The source energy is below the conditioning screen, while its
        # target is finite; the unguarded ratio is huge or nonfinite.
        with np.errstate(divide='ignore', invalid='ignore'):
            coefficient = numerator[singular]/denominator[singular]
        assert np.all((~np.isfinite(coefficient)) | (coefficient > numerator[singular]/threshold))
    assert any(not np.array_equal(a, b) for a, b in zip(actual, cells(expected)))
    for a, b in zip(actual, inputs):
        assert a.shape == b.shape and a.dtype == np.uint8

    # Same forward quantities remove the discrepancy: keep downstream
    # reconstruction, rescaling and casting under strict exact regression.
    pairs = iter(zip(cells(fixture['phases']), cells(fixture['amplitudes'])))
    monkeypatch.setattr(module, '_decompose', lambda a: next(pairs))
    warning = (pytest.warns(RuntimeWarning, match='invalid value encountered in multiply')
               if classification == 'radial_energy' and np.any(denominator[singular] == 0)
               else nullcontext())
    with warning:
        assert_images(operation(inputs, option), expected)


def test_single_pixel_accepted_divergence():
    records = json.loads((FIXTURES/'single_pixel.json').read_text())
    one,many = records
    assert one['step'] == 'NaN' and one['indices'] == 'NaN'
    assert 'subscripts' in one['match_error']
    # Explicit accepted divergence: Python returns the sole target; Octave errors.
    np.testing.assert_array_equal(match_histogram([[17]],[42]),[[42]])
    assert many['step'] == 'Inf' and many['indices'] == '1'
    assert many['match_error'] == '' and many['output'] == '10'
    np.testing.assert_array_equal(match_histogram([[17]],[10,90,200]),[[10]])
