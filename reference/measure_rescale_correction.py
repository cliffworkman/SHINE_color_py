"""Summarize new measurements without overwriting the earlier FFT investigation.

Run after compare_fft_backends --destination reference/diagnostics/nonfinite_rescale
and replay_fft_stages directed at that same directory.
"""
from pathlib import Path
import csv
import hashlib
import json

import numpy as np
from scipy.io import loadmat

from reference.compare_fft_backends import delta, write_csv
from reference.measure_primitives import FIXTURES, cells
from shine_color.numeric import to_uint8
from shine_color.rescale import rescale

DEST = Path(__file__).resolve().parent/'diagnostics/nonfinite_rescale'
HISTORY = DEST.parent/'fft'


def summary(rows):
    return dict(exact=sum(r['unequal']==0 for r in rows),total=len(rows),
        max_abs=max(r['max_abs'] for r in rows),
        pixel_weighted_mean_abs=sum(r['mean_abs']*r['elements'] for r in rows)/sum(r['elements'] for r in rows),
        image_mean_abs=float(np.mean([r['mean_abs'] for r in rows])))


def clean(value):
    if isinstance(value,np.ndarray): return clean(value.tolist())
    if isinstance(value,(list,tuple)): return [clean(v) for v in value]
    if isinstance(value,dict): return {k:clean(v) for k,v in value.items()}
    if isinstance(value,float) and not np.isfinite(value): return str(value)
    return value


def run():
    replay = loadmat(DEST/'octave_stage_replay.mat',simplify_cells=True)
    rows = []
    inverse_comparisons = []
    for trace in replay['traces']:
        if trace['variant'] != 'octave_decomposition': continue
        frozen = loadmat(FIXTURES/(trace['name']+'.mat'))
        pyraw,octraw = trace['python_raw'],trace['octave_raw']
        for k,(a,b) in enumerate(zip(pyraw,octraw)):
            inverse_comparisons.append(dict(fixture=trace['name'],operation=trace['operation'],source=k+1,**delta(a,b)))
        for option in range(3):
            expected = cells(cells(frozen[trace['operation']+'_outputs'])[option])
            paths = dict(
                A=[to_uint8(a*255) for a in pyraw] if option==0 else rescale(pyraw,option),
                B=[to_uint8(a*255) for a in octraw] if option==0 else rescale(octraw,option),
                C=trace['octave_cast_python_raw'] if option==0 else trace['octave_scaling_python_raw'][option-1],
                D=trace['octave_outputs'][option])
            for path,outputs in paths.items():
                for k,(a,b) in enumerate(zip(outputs,expected)):
                    rows.append(dict(path=path,fixture=trace['name'],operation=trace['operation'],
                        option=option,source=k+1,**delta(a,b)))
    write_csv(DEST/'abcd_replay.csv',rows)
    report = dict(replay={p:summary([r for r in rows if r['path']==p]) for p in 'ABCD'},
        backends={},remaining_failures=[],inverse_comparisons=inverse_comparisons,unchanged_evidence_sha256={})
    measurements = list(csv.DictReader((DEST/'output_comparisons.csv').open()))
    backend_info = json.loads((DEST/'backend_diagnostics.json').read_text())
    for row in measurements:
        for field in ('option','source','unequal','nonfinite_pattern_difference','elements'):
            row[field] = int(row[field])
        for field in ('max_abs','mean_abs'): row[field] = float(row[field])
    for runtime in ('octave_default','numpy','fftw_c2c_transposed','fftw_r2c_transposed'):
        group = [r for r in measurements if r['runtime']==runtime]
        report['backends'][runtime] = summary(group)
        if runtime=='octave_default': continue
        failures = [r for r in group if r['unequal']]
        for row in failures:
            sources = backend_info['backend_sources'][runtime][row['fixture']]
            if row['operation']=='spec':
                causes = [i+1 for i,s in enumerate(sources) if
                    s['threshold_localization']['1e-14']['phase_error_low_max']>0.01 and
                    s['threshold_localization']['1e-14']['promoted_spectral_l1_fraction']>0.99]
                category='A'
            else:
                causes = [i+1 for i,s in enumerate(sources) if any(
                    b['retained'] and b['count'] and
                    (float(b['python_source'])<1e-12 or float(b['octave_source'])<1e-12)
                    for b in s['radial_bins'])]
                category='B'
            # These are attribution rules for this measured corpus, not changes
            # to behavior or acceptance tolerances. Fail loudly if unexplained.
            assert causes, row
            direct = row['source'] in causes
            assert direct or row['option']!=0, row
            record = dict(row,category=category,causal_sources=','.join(map(str,causes)),
                propagation='direct' if direct else 'set-wide rescaling from degenerate source')
            report['remaining_failures'].append(record)
    write_csv(DEST/'remaining_failures.csv',report['remaining_failures'])
    probe = loadmat(DEST/'rescale_extrema.mat',simplify_cells=True)
    (DEST/'extrema_observations.json').write_text(json.dumps(clean(probe['cases']),indent=2,allow_nan=False)+'\n')
    for root in (FIXTURES,HISTORY):
        for p in sorted(root.rglob('*')):
            if p.is_file():
                report['unchanged_evidence_sha256'][str(p.relative_to(FIXTURES.parents[2]))]=hashlib.sha256(p.read_bytes()).hexdigest()
    report['classification_note'] = 'A/B attribution includes propagation through correctly implemented set-wide scaling, not a residual D bug. No observed C, D or E failures in the stage controls.'
    (DEST/'corrected_summary.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(replay=report['replay'],backends=report['backends']),indent=2))


if __name__=='__main__': run()
