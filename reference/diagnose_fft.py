"""Characterize the blocked FFT cases without changing either implementation."""
import json
import numpy as np
from scipy.io import loadmat

from reference.measure_primitives import FIXTURES, cells
from shine_color.spatial_frequency import _decompose, _radial_bin_grid


def diagnose():
    records = {}
    for path in sorted(FIXTURES.glob('primitives_*.mat')):
        f = loadmat(path)
        for k,a in enumerate(cells(f['inputs'])):
            p, magnitude = _decompose(a)
            reference = cells(f['amplitudes'])[k]
            phase = cells(f['phases'])[k]
            # Error in complex FFT space is small even when phase error is large.
            actual_fft = np.fft.fftshift(np.fft.fft2(a.astype(float)/255))
            reference_fft = cells(f['spectra'])[k]
            delta = np.abs(actual_fft-reference_fft)
            phase_delta = np.abs(np.exp(1j*p)-np.exp(1j*phase))
            # An empirical diagnostic split, not an acceptance tolerance:
            # coefficients no larger than the measured FFT error floor.
            floor = float(delta.max())
            near_zero = np.maximum(magnitude,reference) <= floor
            radius = _radial_bin_grid(*a.shape)
            bins = int(radius.max())+1
            py_energy = np.bincount(radius.ravel(),weights=magnitude.ravel(),minlength=bins)
            ref_energy = np.bincount(radius.ravel(),weights=reference.ravel(),minlength=bins)
            records[f'{path.stem}/{k}'] = dict(
                complex_fft_max_abs=floor,
                phase_unit_max_abs=float(phase_delta.max()),
                near_zero_count=int(near_zero.sum()),
                phase_error_above_floor=float(phase_delta[~near_zero].max(initial=0)),
                max_reference_amplitude_where_phase_error_exceeds_1e_8=float(reference[phase_delta>1e-8].max(initial=0)),
                python_zero_energy_bins=np.flatnonzero(py_energy==0).tolist(),
                octave_zero_energy_bins=np.flatnonzero(ref_energy==0).tolist(),
                python_radial_energy=py_energy.tolist(),octave_radial_energy=ref_energy.tolist(),
                additive_row_column_image=bool(np.all(a.astype(int)-a[:,0,None].astype(int)-a[0,None,:].astype(int)+int(a[0,0])==0)),
            )
    return records


if __name__ == '__main__':
    records = diagnose()
    (FIXTURES/'fft_diagnosis.json').write_text(json.dumps(records,indent=2)+'\n')
    for key,record in records.items():
        if record['phase_unit_max_abs']>1e-8 or record['octave_zero_energy_bins']:
            print(key,record)
