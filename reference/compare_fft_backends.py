"""Bounded FFT investigation. Generates observations, never modifies test bounds.

Run: python -m reference.compare_fft_backends
Install pyFFTW into ignored reference/.cache/python-fftw or the active environment.
"""
from pathlib import Path
import csv
import hashlib
import json
import platform
import re
import sys
from unittest.mock import patch

import numpy as np
import scipy
from scipy.io import loadmat, savemat

from reference.measure_primitives import FIXTURES, cells
from reference.fft_backends import FFTBackend, OctaveDLLBackend, use_backend
from shine_color import spatial_frequency as sf, spectrum as spec

ROOT = Path(__file__).resolve().parent
DEST = ROOT/'diagnostics/fft'
sys.path.insert(0, str(ROOT/'.cache/python-fftw'))
import pyfftw

THRESHOLDS = (1e-15, 1e-14, 1e-13, 1e-12)


def stats(a):
    a = np.asarray(a)
    finite = a[np.isfinite(a)]
    return dict(minimum=float(finite.min()) if finite.size else None,
                maximum=float(finite.max()) if finite.size else None,
                exact_zero=int(np.count_nonzero(a == 0)),
                nan=int(np.isnan(a).sum()), inf=int(np.isinf(a).sum()),
                below={str(t):int(np.count_nonzero(a < t)) for t in THRESHOLDS})


def delta(a, b):
    a, b = np.asarray(a), np.asarray(b)
    assert a.shape == b.shape
    with np.errstate(invalid='ignore'):
        d = np.abs(a.astype(complex)-b.astype(complex))
    finite = d[np.isfinite(d)]
    return dict(max_abs=float(finite.max()) if finite.size else None,
                mean_abs=float(finite.mean()) if finite.size else None,
                unequal=int(np.count_nonzero(a != b)),
                nonfinite_pattern_difference=int(np.count_nonzero(np.isfinite(a) != np.isfinite(b))),
                elements=int(a.size))


def scalar(value):
    return float(value) if np.isfinite(value) else str(value)


def source_summary(a, fft_a, fft_b, target_a, target_b, mag_b, phase_b):
    # These thresholds classify observations; none is an acceptance tolerance.
    mag_a = np.hypot(fft_a.real, fft_a.imag)
    phase_a = np.angle(fft_a)
    phase_error = np.abs(np.angle(np.exp(1j*(phase_a-phase_b))))
    r = sf._radial_bin_grid(*a.shape)
    n_bins = int(r.max())+1
    sums = lambda x: np.bincount(r.ravel(order='F'), weights=x.ravel(order='F'), minlength=n_bins)
    en_a, en_b = sums(mag_a), sums(mag_b)
    target_en_a, target_en_b = sums(target_a), sums(target_b)
    with np.errstate(divide='ignore', invalid='ignore'):
        ca, cb = target_en_a/en_a, target_en_b/en_b
        post_a = mag_a*ca[r]; post_b = mag_b*cb[r]
    cutoff = np.floor(max(a.shape)/2)
    bin_records = []
    for k in range(n_bins):
        mask = r == k
        bin_records.append(dict(bin=k, retained=bool(k<=cutoff), count=int(mask.sum()),
            python_source=scalar(en_a[k]),octave_source=scalar(en_b[k]),
            python_target=scalar(target_en_a[k]),octave_target=scalar(target_en_b[k]),
            python_coefficient=scalar(ca[k]),octave_coefficient=scalar(cb[k])))
    promoted = target_a*np.exp(1j*phase_a)-target_b*np.exp(1j*phase_b)
    # Unit-norm inverse DFT scaling: sum(abs(spectral error))/N bounds any
    # spatial error before taking real parts, clipping or set-wide rescaling.
    full_budget = float(np.sum(np.abs(promoted))/a.size)
    summaries = {}
    for t in THRESHOLDS:
        low = (mag_a < t) | (mag_b < t)
        outside = ~low
        summaries[str(t)] = dict(count=int(low.sum()),
            phase_error_low_max=float(phase_error[low].max(initial=0)),
            phase_error_other_max=float(phase_error[outside].max(initial=0)),
            target_magnitude_at_low=stats(target_b[low]),
            promoted_spectral_l1_fraction=float(np.sum(np.abs(promoted[low]))/np.sum(np.abs(promoted))) if np.any(promoted) else 0,
            inverse_error_bound_from_low=float(np.sum(np.abs(promoted[low]))/a.size))
    return dict(raw_fft_difference=delta(fft_a,fft_b), python_magnitude=stats(mag_a),
        octave_magnitude=stats(mag_b), phase_error_radians_max=float(phase_error.max()),
        threshold_localization=summaries, radial_bins=bin_records,
        retained_post_sf_python=stats(post_a[r<=cutoff]), retained_post_sf_octave=stats(post_b[r<=cutoff]),
        spec_inverse_error_bound=full_budget,
        additive_row_column_image=bool(np.all(a.astype(int)-a[:,0,None].astype(int)-a[0,None,:].astype(int)+int(a[0,0])==0)))


def write_csv(path, records):
    with path.open('w',newline='') as f:
        writer = csv.DictWriter(f,fieldnames=list(records[0]))
        writer.writeheader(); writer.writerows(records)


def object_cell(items):
    result = np.empty((1,len(items)),dtype=object)
    for k,item in enumerate(items): result[0,k] = item
    return result


def run(destination=DEST, reference_destination=DEST):
    destination = Path(destination)
    reference_destination = Path(reference_destination)
    destination.mkdir(parents=True,exist_ok=True)
    cases = {p.stem:loadmat(p) for p in sorted(FIXTURES.glob('primitives_*.mat'))}
    report = dict(environment=dict(python=platform.python_version(),numpy=np.__version__,
        scipy=scipy.__version__,pyfftw=pyfftw.__version__,
        fftw=re.search(rb'fftw-([^ ]+)',pyfftw.export_wisdom()[0])[1].decode(),
        fftw_compiler=pyfftw.fftw_cc,platform=platform.platform()),
        original_fixture_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(FIXTURES.glob('*')) if p.is_file()},
        thresholds_are_diagnostic_only=True,octave_comparisons={},backend_sources={},
        backend_validation={},interventions={})
    rows = []
    for config in ('default','estimate_1','measure_1'):
        report['octave_comparisons'][config] = {}
        for name,old in cases.items():
            current = loadmat(reference_destination/config/f'{name}.mat')
            record = dict(sources=[],outputs=[])
            for a,b,repeated in zip(cells(current['spectra']),cells(old['spectra']),cells(current['repeated_spectra'])):
                record['sources'].append(dict(vs_frozen=delta(a,b),repeat=delta(a,repeated),
                    phase_radians_max=float(np.max(np.abs(np.angle(np.exp(1j*(np.angle(a)-np.angle(b)))))))))
            for op in ('sf','spec'):
                for option in range(3):
                    for k,(a,b,rep) in enumerate(zip(cells(cells(current[f'{op}_outputs'])[option]),
                        cells(cells(old[f'{op}_outputs'])[option]),cells(cells(current[f'{op}_repeat'])[option]))):
                        record['outputs'].append(dict(operation=op,option=option,source=k+1,
                            vs_frozen=delta(a,b),repeat=delta(a,rep)))
                        rows.append(dict(runtime='octave_'+config,fixture=name,operation=op,option=option,
                            source=k+1,**delta(a,b)))
            report['octave_comparisons'][config][name] = record
    backends = [FFTBackend('numpy'),FFTBackend('fftw_c2c','c2c'),
        FFTBackend('fftw_c2c_transposed','c2c',True),FFTBackend('fftw_r2c_transposed','r2c',True)]
    octave_dll = Path('C:/Program Files/GNU Octave/Octave-11.1.0/mingw64/bin/libfftw3-3.dll')
    if octave_dll.exists():
        direct = OctaveDLLBackend(octave_dll)
        report['environment']['octave_dll_version'] = direct.version
        report['environment']['octave_dll_sha256'] = hashlib.sha256(octave_dll.read_bytes()).hexdigest()
        backends.append(direct)
    traces = []
    for backend in backends:
        pyfftw.forget_wisdom()
        # Adapter verification on nondegenerate complex and real input.
        x = np.arange(35).reshape(5,7).astype(float)
        transformed = backend.fft2(x)
        report['backend_validation'][backend.name] = dict(
            real_fft_vs_numpy=delta(transformed,np.fft.fft2(x)),
            normalized_roundtrip=delta(backend.ifft2(transformed),x),
            complex_inverse_vs_numpy=delta(backend.ifft2(x+1j*x[::-1]),np.fft.ifft2(x+1j*x[::-1])))
        report['backend_sources'][backend.name] = {}
        for name,old in cases.items():
            inputs = cells(old['inputs'])
            reference = loadmat(reference_destination/'default'/f'{name}.mat')
            transforms = [np.fft.fftshift(backend.fft2(a.astype(float)/255)) for a in inputs]
            target = np.mean([np.hypot(a.real,a.imag) for a in transforms],axis=0)
            reference_target = np.mean(cells(reference['amplitudes']),axis=0)
            source_records = []
            for k,(a,fft_a,fft_b) in enumerate(zip(inputs,transforms,cells(reference['spectra']))):
                detail = source_summary(a,fft_a,fft_b,target,reference_target,
                    cells(reference['amplitudes'])[k],cells(reference['phases'])[k])
                detail['normalized_input_difference'] = delta(a.astype(float)/255,cells(reference['normalized'])[k])
                source_records.append(detail)
            report['backend_sources'][backend.name][name] = source_records
            with use_backend(backend):
                for op,func in [('sf',sf.sf_match),('spec',spec.spec_match)]:
                    for option in range(3):
                        outputs = func(inputs,option)
                        for k,(a,b) in enumerate(zip(outputs,cells(cells(old[f'{op}_outputs'])[option]))):
                            rows.append(dict(runtime=backend.name,fixture=name,operation=op,option=option,
                                source=k+1,**delta(a,b)))
                # Separate arithmetic-form intervention: sqrt vs hypot only.
                for op,module,func in [('sf',sf,sf.sf_match),('spec',spec,spec.spec_match)]:
                    def sqrt_decompose(a):
                        z = np.fft.fftshift(backend.fft2(np.asarray(a,dtype=float)/255))
                        return np.arctan2(z.imag,z.real),np.sqrt(z.real**2+z.imag**2)
                    with patch.object(module,'_decompose',sqrt_decompose):
                        for option in range(3):
                            for k,(a,b) in enumerate(zip(func(inputs,option),cells(cells(old[f'{op}_outputs'])[option]))):
                                rows.append(dict(runtime=backend.name+'_sqrt',fixture=name,operation=op,option=option,
                                    source=k+1,**delta(a,b)))
    # Causal intervention: feed exactly the observed Octave decomposition into
    # the EXISTING Python functions, capture their inverse inputs/raw outputs.
    # This bypasses source FFT/phase/magnitude math without changing algorithms.
    for name,old in cases.items():
        inputs = cells(old['inputs']); ref = loadmat(reference_destination/'default'/f'{name}.mat')
        for op,module,func in [('sf',sf,sf.sf_match),('spec',spec,spec.spec_match)]:
            for variant in ('native','octave_decomposition'):
                original_inverse = np.fft.ifft2
                inverse_inputs,raw = [],[]
                def capture(x):
                    inverse_inputs.append(np.array(x,copy=True))
                    result = original_inverse(x)
                    raw.append(result.real.copy())
                    return result
                pairs = iter(zip(cells(ref['phases']),cells(ref['amplitudes'])))
                decompose = module._decompose
                if variant == 'octave_decomposition':
                    decompose = lambda image: next(pairs)
                with patch.object(module,'_decompose',decompose),patch.object(np.fft,'ifft2',capture):
                    func(inputs,0)
                trace = dict(name=name,operation=op,variant=variant,
                    inverse_inputs=object_cell(inverse_inputs),python_raw=object_cell(raw))
                traces.append(trace)
                key=f'{name}/{op}/{variant}'
                report['interventions'][key] = dict(raw=[stats(a) for a in raw])
    # A small independent nonfinite reduction probe, separate from kernel edits.
    nan_inputs = object_cell([np.full((2,2),np.nan),np.array([[0.,10.],[20.,30.]])])
    savemat(destination/'python_stage_inputs.mat',dict(traces=object_cell(traces),nan_inputs=nan_inputs),do_compression=True)
    write_csv(destination/'output_comparisons.csv',rows)
    report['output_summary'] = {runtime:dict(exact=sum(r['unequal']==0 for r in rows if r['runtime']==runtime),
        total=sum(r['runtime']==runtime for r in rows),max_abs=max(r['max_abs'] for r in rows if r['runtime']==runtime))
        for runtime in dict.fromkeys(r['runtime'] for r in rows)}
    (destination/'backend_diagnostics.json').write_text(json.dumps(report,separators=(',',':'),allow_nan=False)+'\n')
    print(json.dumps(report['output_summary'],indent=2))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--destination',type=Path,default=DEST)
    parser.add_argument('--reference-destination',type=Path,default=DEST)
    args = parser.parse_args()
    run(args.destination,args.reference_destination)
