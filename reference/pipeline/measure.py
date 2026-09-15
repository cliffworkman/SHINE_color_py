"""Boundary-specific pipeline evidence; never regenerate acceptance tolerances."""
from contextlib import ExitStack
import hashlib
import json
import platform
from pathlib import Path
from unittest.mock import patch
import numpy as np
import scipy
import skimage
from scipy.io import loadmat

from shine_color import pipeline, color, histogram, luminance, spatial_frequency, spectrum
from shine_color.numeric import imhist256
from reference.backend_policy.screen_conditioning import characterize

ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/'tests/reference/fixtures/pipeline'
SPACES={1:'RGB',2:'HSV',3:'CIELab'}
OPS={'lumMatch':luminance.lum_match,'histMatch':histogram.hist_match,'sfMatch':spatial_frequency.sf_match,'specMatch':spectrum.spec_match}


def as_list(value):
    if isinstance(value,dict): return [value]
    if isinstance(value,list): return value
    return list(np.asarray(value,dtype=object).ravel())


def load_group(name):
    result=loadmat(DEST/(name+'_reference.mat'),simplify_cells=True)
    for run in as_list(result['runs']):
        for key in ('colorspace','mode','iterations','rescale_option'): run[key]=int(run[key])
    return result


def delta(actual, expected):
    differences=[np.abs(np.asarray(a,dtype=float)-np.asarray(b,dtype=float)) for a,b in zip(actual,expected)]
    assert len(actual)==len(expected)
    for a,b in zip(actual,expected): assert a.shape==b.shape
    count=sum(d.size for d in differences)
    return dict(max_abs=max(float(d.max()) for d in differences),mean_abs=sum(float(d.sum()) for d in differences)/count,
        unequal=sum(int(np.count_nonzero(d)) for d in differences),elements=count)


def execute(inputs,run,replay_hist=False, details=False, octave_chroma=False):
    """Instrument only boundaries; optional exact Octave histogram replay."""
    active=[0,1,2] if run['colorspace']==1 else ([2] if run['colorspace']==2 else [0])
    stage_list=as_list(run['stages']); working=[]; natives=[]; injected=[]
    original_process=pipeline._process_channel
    original_hist=histogram.hist_match
    original_merge=getattr(color,{1:'merge_rgb',2:'merge_hsv',3:'merge_lab'}[run['colorspace']])
    channel_index=iter(active)
    def process(images,mode,iterations,rescale_option):
        channel=next(channel_index)
        queue=iter([s for s in stage_list if s['channel']==channel+1 and s['operation']=='histMatch'])
        def hist(images,rng=None):
            if not replay_hist: return original_hist(images,rng=rng)
            stage=next(queue)
            injected.append(delta(images,as_list(stage['input'])))
            return [a.copy() for a in as_list(stage['output'])]
        with patch.object(histogram,'hist_match',hist):
            result=original_process(images,mode,iterations,rescale_option)
        working.append(delta(result,list(run['working'][channel,:])))
        return result
    def merge(*args):
        result=original_merge(*args)
        natives.append(result.astype(float)/255 if run['colorspace']==1 else result.copy())
        return result
    with ExitStack() as stack:
        stack.enter_context(patch.object(pipeline,'_process_channel',process))
        stack.enter_context(patch.object(color,original_merge.__name__,merge))
        if octave_chroma and run['colorspace']!=1:
            method='split_hsv' if run['colorspace']==2 else 'split_lab'
            original_split=getattr(color,method)
            source_index=iter(range(len(inputs)))
            def split(image):
                i=next(source_index); parts=list(original_split(image))
                for ch in ((0,1) if run['colorspace']==2 else (1,2)):
                    parts[ch]=run['seed'][ch,i].copy()
                return tuple(parts)
            stack.enter_context(patch.object(color,method,split))
        output=pipeline.run(inputs,SPACES[run['colorspace']],run['mode'],run['iterations'],run['rescale_option'])
    result=dict(working=working,native=delta(natives,as_list(run['native_rgb'])),terminal=delta(output,as_list(run['terminal'])),injected_inputs=injected)
    if details: result.update(native_arrays=natives,terminal_arrays=output)
    return result


def measure():
    records=[]; stage_records=[]; bounds={}; failures=[]
    manifest=json.loads((DEST/'inputs.json').read_text())
    for group in manifest['groups']:
        name=group['name']; f=load_group(name); inputs=as_list(f['rgb'])
        for r in as_list(f['runs']):
            identity=dict(group=name,colorspace=SPACES[r['colorspace']],mode=int(r['mode']),iterations=int(r['iterations']),rescale_option=int(r['rescale_option']))
            # All runs use frozen random-stage output only when histogram is present.
            result=execute(inputs,r,replay_hist=r['mode'] in (2,5,6,7,8))
            if result['terminal']['unequal'] or any(d['unequal'] for d in result['working']+result['injected_inputs']):
                failures.append(dict(**identity,path='full_replay',result=result))
            bounds[identity['colorspace']]=max(bounds.get(identity['colorspace'],0),result['native']['max_abs'])
            condition=[]; hist_count=0; spectral_count=0
            for index,s in enumerate(as_list(r['stages'])):
                a=as_list(s['input']); b=as_list(s['output']); op=s['operation']
                if op=='histMatch':
                    target=histogram.average_histogram(a)
                    assert np.array_equal(target,np.asarray(s['target_histogram']).ravel())
                    actual=histogram.hist_match(a,rng=np.random.default_rng(913+index))
                    check=delta([imhist256(v) for v in actual],[np.asarray(v).ravel() for v in as_list(s['output_histograms'])])
                    hist_count+=1
                    if check['unequal']: failures.append(dict(**identity,path='histogram',index=index,delta=check))
                    stage_records.append(dict(**identity,index=index,operation=op,delta=check))
                elif op in ('sfMatch','specMatch'):
                    actual=OPS[op](a,r['rescale_option']); check=delta(actual,b)
                    c=[characterize(v) for v in as_list(s['amplitudes'])]
                    # Compact per-image screen, no huge radial-bin tables in this report.
                    for item in c: item.pop('retained_bins')
                    py_c=[characterize(spatial_frequency._decompose(v)[1]) for v in a]
                    for item in py_c: item.pop('retained_bins')
                    passes=all(item['passes'] for item in c+py_c)
                    condition.append(passes); spectral_count+=1
                    stage_records.append(dict(**identity,index=index,operation=op,channel=int(s['channel']),iteration=int(s['iteration']),
                        conditioning=c,python_conditioning=py_c,screen_pass=passes,delta=check))
                    if check['unequal']: failures.append(dict(**identity,path='spectral_stage',index=index,screen_pass=passes,delta=check))
            records.append(dict(**identity,classification='exact deterministic parity' if r['mode'] in (1,3,4) else 'histogram invariant and staged replay parity',
                result=result,histogram_stages=hist_count,spectral_stages=spectral_count,all_spectral_inputs_screened=all(condition)))
        print(name,'completed',len(records),'runs; failures',len(failures),flush=True)
    summary=dict(runs=len(records),deterministic_runs=sum(r['mode'] in (1,3,4) for r in records),
        histogram_runs=sum(r['mode'] in (2,5,6,7,8) for r in records),
        spectral_stages=sum(r['spectral_stages'] for r in records),histogram_stages=sum(r['histogram_stages'] for r in records),
        degenerate_spectral_stages=sum(s.get('screen_pass') is False for s in stage_records),
        native_rgb_maxima=bounds,failures=len(failures))
    report=dict(summary=summary,runs=records,stages=stage_records,failures=failures,
        environment=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,skimage=skimage.__version__,platform=platform.platform()),
        fixture_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in DEST.glob('*.mat')})
    (DEST/'measurements.json').write_text(json.dumps(report,separators=(',',':'))+'\n',newline='\n')
    print(json.dumps(summary,indent=2)); print(json.dumps(failures[:10],indent=2))


if __name__=='__main__': measure()
