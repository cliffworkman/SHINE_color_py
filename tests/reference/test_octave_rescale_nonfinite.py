"""Octave 11.1.0 semantic evidence, not a generic NaN policy."""
from pathlib import Path
import warnings

import numpy as np
import pytest
from scipy.io import loadmat

from shine_color.rescale import rescale, _extreme

PROBE = Path(__file__).resolve().parents[2]/'reference/diagnostics/nonfinite_rescale/rescale_extrema.mat'
CASES = loadmat(PROBE,simplify_cells=True)['cases']


def images(value):
    return list(value.ravel()) if value.dtype == object else [value]


@pytest.mark.parametrize('case',CASES,ids=lambda c:c['name'])
def test_octave_extrema_reductions(case):
    inputs = images(case['inputs'])
    bright = np.array([_extreme(a,True) for a in inputs])
    dark = np.array([_extreme(a,False) for a in inputs])
    np.testing.assert_array_equal(bright,np.atleast_1d(case['brightests']))
    np.testing.assert_array_equal(dark,np.atleast_1d(case['darkests']))
    with np.errstate(invalid='ignore'):
        actual = [_extreme(bright,True),_extreme(dark,False),bright.mean(),dark.mean()]
    np.testing.assert_array_equal(actual,case['extrema'])


@pytest.mark.parametrize('case',CASES,ids=lambda c:c['name'])
@pytest.mark.parametrize('option',[1,2])
def test_octave_nonfinite_rescale(case,option):
    assert np.asarray(case['extrema_warning']).size == 0
    assert np.asarray(case['warnings'][option-1]).size == 0
    assert np.asarray(case['errors'][option-1]).size == 0
    inputs = images(case['inputs'])
    originals = [a.copy() for a in inputs]
    with warnings.catch_warnings(record=True) as emitted:
        warnings.simplefilter('always')
        actual = rescale(inputs,option)
    expected = images(case['outputs'][option-1])
    assert len(actual) == len(expected)
    for a,b in zip(actual,expected):
        assert a.shape == b.shape and a.dtype == b.dtype == np.uint8
        np.testing.assert_array_equal(a,b)
    assert not emitted, [str(w.message) for w in emitted]
    for a,b in zip(inputs,originals):
        np.testing.assert_array_equal(a,b)
