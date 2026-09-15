"""Localize new pipeline differences without changing any production algorithms."""
from collections import Counter
import json
from unittest.mock import patch
import numpy as np
from shine_color import spectrum,spatial_frequency,color
from shine_color.numeric import to_uint8
from .measure import DEST,SPACES,as_list,load_group,execute,delta
from reference.backend_policy.screen_conditioning import characterize


def diagnose():
    report=json.loads((DEST/'measurements.json').read_text())
    pixels=[]; cross=[]; spectral=[]; cache={}
    for record in report['runs']:
        name=record['group']
        if name not in cache: cache[name]=load_group(name)
        f=cache[name]
        run=next(r for r in as_list(f['runs']) if SPACES[r['colorspace']]==record['colorspace'] and all(r[k]==record[k] for k in ('mode','iterations','rescale_option')))
        identity={k:record[k] for k in ('group','colorspace','mode','iterations','rescale_option')}
        if record['colorspace']=='HSV' and record['result']['terminal']['unequal']:
            actual=execute(as_list(f['rgb']),run,True,details=True)
            same_chroma=execute(as_list(f['rgb']),run,True,octave_chroma=True)
            ref_native=as_list(run['native_rgb']); ref_terminal=as_list(run['terminal'])
            cross.append(dict(**identity,octave_chroma_reconstruction=same_chroma,
                python_cast_of_octave_native=delta([to_uint8(a*255) for a in ref_native],ref_terminal)))
            for i,(a,b,py_native,oct_native) in enumerate(zip(actual['terminal_arrays'],ref_terminal,actual['native_arrays'],ref_native)):
                for coord in np.argwhere(a!=b):
                    loc=tuple(coord); py_scaled=float(py_native[loc]*255); oct_scaled=float(oct_native[loc]*255)
                    half=float(np.floor(oct_scaled)+.5)
                    pixels.append(dict(**identity,source=i+1,index=coord.tolist(),original_rgb=f['rgb'][i][loc[:2]].tolist(),
                        python_scaled=py_scaled,octave_scaled=oct_scaled,nearest_half=half,
                        python_distance_half=py_scaled-half,octave_distance_half=oct_scaled-half,
                        python_terminal=int(a[loc]),octave_terminal=int(b[loc]),
                        python_cast_same_octave_native=int(to_uint8(oct_scaled))))
        for index,stage in enumerate(as_list(run['stages'])):
            if stage['operation'] not in ('sfMatch','specMatch'): continue
            stats=[characterize(a) for a in as_list(stage['amplitudes'])]
            if all(s['passes'] for s in stats): continue
            module=spectrum if stage['operation']=='specMatch' else spatial_frequency
            func=module.spec_match if stage['operation']=='specMatch' else module.sf_match
            input=as_list(stage['input']); expected=as_list(stage['output'])
            before=delta(func(input,run['rescale_option']),expected)
            pairs=iter(zip(as_list(stage['phases']),as_list(stage['amplitudes'])))
            with patch.object(module,'_decompose',lambda a:next(pairs)):
                after=delta(func(input,run['rescale_option']),expected)
            localized=[]
            for i,(image,ref_amp,ref_phase) in enumerate(zip(input,as_list(stage['amplitudes']),as_list(stage['phases']))):
                phase,amp=spatial_frequency._decompose(image)
                threshold=1e-10*max(1,float(ref_amp.max()))
                low=(ref_amp<=threshold)|(amp<=threshold)
                gap=np.abs(np.exp(1j*phase)-np.exp(1j*ref_phase))
                localized.append(dict(source=i+1,near_zero=int(low.sum()),
                    phase_gap_near_zero=float(gap[low].max(initial=0)),phase_gap_elsewhere=float(gap[~low].max(initial=0))))
            spectral.append(dict(**identity,index=index,operation=stage['operation'],channel=int(stage['channel']),iteration=int(stage['iteration']),
                ordinary=before,octave_forward_injected=after,localization=localized))
    summary=dict(hsv_failing_runs=len(cross),hsv_unequal_scalar_outputs=len(pixels),
        hsv_max_distance_half=max(max(abs(p['python_distance_half']),abs(p['octave_distance_half'])) for p in pixels),
        same_native_cast_failing_runs=sum(r['python_cast_of_octave_native']['unequal']>0 for r in cross),
        same_native_cast_unequal=sum(r['python_cast_of_octave_native']['unequal'] for r in cross),
        octave_chroma_failing_runs=sum(r['octave_chroma_reconstruction']['terminal']['unequal']>0 for r in cross),
        degenerate_stages=len(spectral),degenerate_output_mismatches=sum(s['ordinary']['unequal']>0 for s in spectral),
        injected_spectral_mismatches=sum(s['octave_forward_injected']['unequal'] for s in spectral))
    (DEST/'diagnosis.json').write_text(json.dumps(dict(summary=summary,hsv_pixels=pixels,hsv_cross_replays=cross,spectral=spectral),indent=2)+'\n',newline='\n')
    print(json.dumps(summary,indent=2)); print(json.dumps(pixels[:6],indent=2))


if __name__=='__main__': diagnose()
