"""Remeasure the frozen 480-run corpus under the approved per-stage contract.

Writes new completion records; never replaces the original diagnostic records.
"""
import csv
import hashlib
import json
import platform
from unittest.mock import patch
import numpy as np
import scipy
from shine_color import spatial_frequency,spectrum,histogram
from shine_color.numeric import imhist256
from reference.backend_policy.screen_conditioning import characterize
from .measure import DEST,SPACES,OPS,as_list,load_group,execute,delta


def exact(result):
    return result['terminal']['unequal']==0 and all(d['unequal']==0 for d in result['working']+result['injected_inputs']) and all(
        d['input_delta']['unequal']==d['replay']['unequal']==0 for d in result['forward_replays'])


def measure():
    old=json.loads((DEST/'measurements.json').read_text())
    for name,digest in old['fixture_sha256'].items():
        assert hashlib.sha256((DEST/name).read_bytes()).hexdigest()==digest
    records=[]; stages=[]
    for group in json.loads((DEST/'inputs.json').read_text())['groups']:
        name=group['name']; f=load_group(name)
        for run in as_list(f['runs']):
            identity=dict(group=name,colorspace=SPACES[run['colorspace']],**{k:run[k] for k in ('mode','iterations','rescale_option')})
            degenerate=0
            for index,s in enumerate(as_list(run['stages'])):
                a=as_list(s['input']); expected=as_list(s['output']); op=s['operation']
                if op=='histMatch':
                    actual=histogram.hist_match(a,rng=np.random.default_rng(391))
                    target=histogram.average_histogram(a)
                    assert np.array_equal(target,np.asarray(s['target_histogram']).ravel())
                    d=delta([imhist256(v) for v in actual],[imhist256(v) for v in expected])
                    stages.append(dict(**identity,index=index,operation=op,delta=d,accepted=d['unequal']==0))
                elif op in ('sfMatch','specMatch'):
                    stats=[characterize(v) for v in as_list(s['amplitudes'])]
                    py_stats=[characterize(spatial_frequency._decompose(v)[1]) for v in a]
                    passes=all(v['passes'] for v in stats+py_stats)
                    module=spatial_frequency if op=='sfMatch' else spectrum
                    ordinary=delta(OPS[op](a,run['rescale_option']),expected)
                    replay=None
                    if not passes:
                        degenerate+=1
                        pairs=iter(zip(as_list(s['phases']),as_list(s['amplitudes'])))
                        with patch.object(module,'_decompose',lambda image:next(pairs)):
                            replay=delta(OPS[op](a,run['rescale_option']),expected)
                    for v in stats+py_stats: v.pop('retained_bins')
                    stages.append(dict(**identity,index=index,operation=op,screen_pass=passes,
                        conditioning=stats,python_conditioning=py_stats,ordinary=ordinary,common_forward=replay,
                        accepted=(ordinary if passes else replay)['unequal']==0))
            ordinary=execute(as_list(f['rgb']),run,replay_hist=run['mode'] in (2,5,6,7,8))
            contract=execute(as_list(f['rgb']),run,replay_hist=True,common_forward_degenerate=True) if not exact(ordinary) else ordinary
            records.append(dict(**identity,ordinary=ordinary,contract=contract,ordinary_exact=exact(ordinary),
                accepted=exact(contract),degenerate_stages=degenerate,
                classification='positive degeneracy + common-forward chain' if not exact(ordinary) else
                    ('deterministic exact' if run['mode'] in (1,3,4) else 'histogram invariant + captured replay')))
        print(name,'complete',flush=True)
    spectral=[s for s in stages if s['operation'] in ('sfMatch','specMatch')]
    hist=[s for s in stages if s['operation']=='histMatch']
    summary=dict(configurations=len(records),accepted=sum(r['accepted'] for r in records),
        ordinary_exact=sum(r['ordinary_exact'] for r in records),
        positive_degeneracy_configurations=sum(not r['ordinary_exact'] for r in records),
        histogram_stages=len(hist),histogram_passed=sum(s['accepted'] for s in hist),
        spectral_stages=len(spectral),well_conditioned=sum(s['screen_pass'] for s in spectral),
        well_conditioned_exact=sum(s['screen_pass'] and s['ordinary']['unequal']==0 for s in spectral),
        degenerate_stages=sum(not s['screen_pass'] for s in spectral),
        degenerate_common_forward_exact=sum(not s['screen_pass'] and s['common_forward']['unequal']==0 for s in spectral),
        hsv_terminal_unequal=sum(r['ordinary']['terminal']['unequal'] for r in records if r['colorspace']=='HSV'),
        native_maxima={space:max(r['contract']['native']['max_abs'] for r in records if r['colorspace']==space) for space in SPACES.values()},
        unexplained_failures=sum(not r['accepted'] for r in records)+sum(not s['accepted'] for s in stages))
    output=dict(summary=summary,runs=records,stages=stages,fixture_sha256=old['fixture_sha256'],
        environment=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,platform=platform.platform()))
    (DEST/'completion_measurements.json').write_text(json.dumps(output,separators=(',',':'))+'\n',newline='\n')
    rows=[]
    for space in SPACES.values():
        for mode in range(1,9):
            for it in (1,2):
                selected=[r for r in records if r['colorspace']==space and r['mode']==mode and r['iterations']==it]
                rows.append(dict(colorspace=space,mode=mode,iterations=it,configurations=len(selected),
                    ordinary_exact=sum(r['ordinary_exact'] for r in selected),
                    positive_degeneracy=sum(not r['ordinary_exact'] for r in selected),accepted=sum(r['accepted'] for r in selected)))
    with (DEST/'completion_matrix.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    print(json.dumps(summary,indent=2))


if __name__=='__main__': measure()
