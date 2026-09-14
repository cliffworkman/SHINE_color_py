"""Join stage replays and backend observations into compact diagnostic records."""
import csv
import json
import numpy as np
from scipy.io import loadmat

from reference.compare_fft_backends import DEST, delta, stats, write_csv
from reference.measure_primitives import FIXTURES, cells
from shine_color.numeric import to_uint8
from shine_color.rescale import rescale


def summarize():
    data = loadmat(DEST/'octave_stage_replay.mat',simplify_cells=True)
    report = dict(traces={}, nan_rescale_probe={})
    rows = []
    for t in data['traces']:
        old = loadmat(FIXTURES/(t['name']+'.mat'))
        raw,octraw = t['python_raw'],t['octave_raw']
        record = dict(inverse_differences=[delta(a,b) for a,b in zip(raw,octraw)],
            python_raw=[stats(a) for a in raw],octave_raw=[stats(a) for a in octraw],
            same_raw_scaling={},final_outputs={})
        for option in range(3):
            expected = cells(cells(old[t['operation']+'_outputs'])[option])
            python_outputs = [to_uint8(a*255) for a in raw] if option==0 else rescale(raw,option)
            oct_outputs = t['octave_outputs'][option]
            record['final_outputs'][str(option)] = dict(
                python=[delta(a,b) for a,b in zip(python_outputs,expected)],
                octave_inverse_and_scaling=[delta(a,b) for a,b in zip(oct_outputs,expected)])
            for runtime,outputs in [('python',python_outputs),('octave_inverse_and_scaling',oct_outputs)]:
                for k,(a,b) in enumerate(zip(outputs,expected)):
                    rows.append(dict(fixture=t['name'],operation=t['operation'],variant=t['variant'],
                        runtime=runtime,option=option,source=k+1,**delta(a,b)))
            if option:
                record['same_raw_scaling'][str(option)] = [delta(a,b) for a,b in
                    zip(python_outputs,t['octave_scaling_python_raw'][option-1])]
        report['traces'][f"{t['name']}/{t['operation']}/{t['variant']}"] = record
    for option in (1,2):
        py = rescale(data['nan_inputs'],option)
        octout = data['nan_outputs'][option-1]
        report['nan_rescale_probe'][str(option)] = dict(
            python=[a.tolist() for a in py],octave=[a.tolist() for a in octout],
            difference=[delta(a,b) for a,b in zip(py,octout)])
    report['summary'] = {}
    for variant in ('native','octave_decomposition'):
        for runtime in ('python','octave_inverse_and_scaling'):
            selected=[r for r in rows if r['variant']==variant and r['runtime']==runtime]
            report['summary'][variant+'/'+runtime] = dict(exact=sum(r['unequal']==0 for r in selected),
                total=len(selected),max_abs=max(r['max_abs'] for r in selected))
    (DEST/'stage_summary.json').write_text(json.dumps(report,separators=(',',':'),allow_nan=False)+'\n')
    write_csv(DEST/'stage_output_comparisons.csv',rows)
    backend = json.loads((DEST/'backend_diagnostics.json').read_text())
    output_rows = list(csv.DictReader((DEST/'output_comparisons.csv').open()))
    failures = []
    failed_groups = {(r['fixture'],r['operation'],r['option']) for r in output_rows
        if r['runtime']=='numpy' and int(r['unequal'])>0}
    assert len(failed_groups)==18, 'Existing failures changed; investigate before updating the report.'
    for row in output_rows:
        if row['runtime']!='numpy' or (row['fixture'],row['operation'],row['option']) not in failed_groups:
            continue
        source=backend['backend_sources']['numpy'][row['fixture']][int(row['source'])-1]
        record=dict(fixture=row['fixture'],operation=row['operation'],option=int(row['option']),
            source=int(row['source']),output_max_abs=float(row['max_abs']),
            output_unequal=int(row['unequal']),raw_fft_max_abs=source['raw_fft_difference']['max_abs'],
            python_mag_min=source['python_magnitude']['minimum'],octave_mag_min=source['octave_magnitude']['minimum'],
            python_mag_max=source['python_magnitude']['maximum'],octave_mag_max=source['octave_magnitude']['maximum'],
            python_exact_zeros=source['python_magnitude']['exact_zero'],octave_exact_zeros=source['octave_magnitude']['exact_zero'],
            phase_error_max_rad=source['phase_error_radians_max'],
            spec_promoted_error_fraction_below_1e_14=source['threshold_localization']['1e-14']['promoted_spectral_l1_fraction'])
        for t in ('1e-15','1e-14','1e-13','1e-12'):
            for runtime in ('python','octave'):
                record[f'{runtime}_below_{t}']=source[runtime+'_magnitude']['below'][t]
        failures.append(record)
    assert len(failures)==54
    write_csv(DEST/'failing_cases.csv',failures)
    print(json.dumps(report['summary'],indent=2))


if __name__ == '__main__':
    summarize()
