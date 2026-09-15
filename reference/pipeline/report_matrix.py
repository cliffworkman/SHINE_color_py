"""Compact acceptance matrix from frozen measurements; failures remain explicit."""
import csv
import json
from .measure import DEST


def report():
    measurement=json.loads((DEST/'measurements.json').read_text())
    rows=[]
    for space in ('RGB','HSV','CIELab'):
        for mode in range(1,9):
            for iterations in (1,2):
                runs=[r for r in measurement['runs'] if r['colorspace']==space and r['mode']==mode and r['iterations']==iterations]
                output_failures=sum(r['result']['terminal']['unequal']>0 for r in runs)
                working_failures=sum(any(d['unequal'] for d in r['result']['working']) for r in runs)
                injection_failures=sum(any(d['unequal'] for d in r['result']['injected_inputs']) for r in runs)
                degeneracy=sum(not r['all_spectral_inputs_screened'] for r in runs)
                status='exact deterministic parity' if mode in (1,3,4) else 'histogram invariant + staged replay parity'
                if space=='HSV' and output_failures: status+='; BLOCKED: terminal quantization'
                if degeneracy: status+='; recorded spectral degeneracy'
                if working_failures or injection_failures: status+='; full replay nonexact'
                rows.append(dict(colorspace=space,mode=mode,iterations=iterations,configurations=len(runs),
                    exact_terminal_runs=len(runs)-output_failures,working_failure_runs=working_failures,
                    histogram_input_failure_runs=injection_failures,degenerate_runs=degeneracy,status=status))
    with (DEST/'acceptance_matrix.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    compact={}
    for space in ('RGB','HSV','CIELab'):
        for mode in range(1,9):
            runs=[r for r in measurement['runs'] if r['colorspace']==space and r['mode']==mode]
            compact[f'{space}/{mode}']=dict(exact=sum(r['result']['terminal']['unequal']==0 for r in runs),total=len(runs))
    print(json.dumps(compact,indent=2))


if __name__=='__main__': report()
