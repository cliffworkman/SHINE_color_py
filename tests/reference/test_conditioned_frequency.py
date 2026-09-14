"""Corpus-bound exact parity; no Octave executable, pyFFTW or ignored cache needed."""
from functools import lru_cache
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from scipy.io import loadmat
from shine_color.spatial_frequency import sf_match, _decompose
from shine_color.spectrum import spec_match
from reference.backend_policy.screen_conditioning import characterize

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT/'reference/backend_policy'
FIXTURES = Path(__file__).with_name('fixtures')/'conditioned'
MANIFEST = json.loads((STUDY/'corpus_manifest.json').read_text())
SCREEN = json.loads((STUDY/'conditioning.json').read_text())
PROVENANCE = json.loads((FIXTURES/'provenance.json').read_text())


@lru_cache(maxsize=9)
def conditioned_group(name):
    source = STUDY/'data'/(name+'_inputs.mat')
    expected = FIXTURES/(name+'_outputs.mat')
    assert hashlib.sha256(source.read_bytes()).hexdigest() == MANIFEST['input_sha256'][source.name]
    assert hashlib.sha256(expected.read_bytes()).hexdigest() == PROVENANCE['output_sha256'][expected.name]
    assert hashlib.sha256((STUDY/'CRITERIA.md').read_bytes()).hexdigest() == SCREEN['criteria_sha256'] == MANIFEST['criteria_sha256']
    reference = next(g for g in SCREEN['groups'] if g['name'] == name)
    inputs = list(loadmat(source)['inputs'].ravel())
    for image, recorded in zip(inputs, reference['sources']):
        # Both the exported Octave evidence and current NumPy decomposition
        # must pass the unchanged predeclared criterion before parity checks.
        assert recorded['min_magnitude'] > recorded['scaled_threshold']
        assert recorded['min_retained_denominator'] > recorded['scaled_threshold']
        assert recorded['scaled_threshold'] == 1e-10*max(1, recorded['max_magnitude'])
        assert characterize(_decompose(image)[1])['passes']
    return inputs, loadmat(expected)


@pytest.mark.parametrize('name', [pytest.param(g['name'],
    marks=[pytest.mark.octave_natural_image] if g['kind'] == 'natural_sample' else [])
    for g in MANIFEST['groups']])
@pytest.mark.parametrize('op', ['sf', 'spec'])
@pytest.mark.parametrize('option', [0, 1, 2])
def test_exact_conditioned_frequency(name, op, option):
    inputs, fixture = conditioned_group(name)
    operation = sf_match if op == 'sf' else spec_match
    expected = fixture[op+'_outputs'].ravel()[option].ravel()
    actual = operation(inputs, option)
    assert len(actual) == len(expected) == 3
    for a, b in zip(actual, expected):
        assert a.dtype == b.dtype == np.uint8
        np.testing.assert_array_equal(a, b)
