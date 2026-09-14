"""Final-output comparison after independent Octave conditioning screen."""
from collections import Counter
import hashlib
import json
from unittest.mock import patch
import numpy as np
from scipy.io import loadmat
from reference.compare_fft_backends import delta,write_csv,pyfftw
from reference.fft_backends import FFTBackend,use_backend
from reference.measure_primitives import cells
from shine_color import spatial_frequency as sf,spectrum as spec
from .build_corpus import ROOT,DATA
from .screen_conditioning import CACHE,characterize


def summarize(rows):
    histogram=Counter()
    for r in rows: histogram.update(r['nonzero_distribution'])
    return dict(exact_images=sum(r['unequal']==0 for r in rows),images=len(rows),
        max_abs=max(r['max_abs'] for r in rows),pixel_weighted_mae=sum(r['mean_abs']*r['elements'] for r in rows)/sum(r['elements'] for r in rows),
        mean_image_mae=float(np.mean([r['mean_abs'] for r in rows])),nonzero_distribution=dict(histogram),
        pixels=sum(r['elements'] for r in rows))


def run():
    manifest=json.loads((ROOT/'corpus_manifest.json').read_text())
    screened=json.loads((ROOT/'conditioning.json').read_text())
    assert manifest['criteria_sha256']==screened['criteria_sha256']
    records=[]; intermediates=[]
    for group in manifest['groups']:
        name=group['name']
        f=loadmat(DATA/(name+'_inputs.mat')); inputs=cells(f['inputs'])
        reference=loadmat(CACHE/(name+'_spectra.mat'))
        expected=loadmat(CACHE/(name+'_outputs.mat'))
        oldscreen=next(g for g in screened['groups'] if g['name']==name)
        assert hashlib.sha256((CACHE/(name+'_spectra.mat')).read_bytes()).hexdigest()==oldscreen['spectra_sha256']
        for backend in (FFTBackend('numpy'),FFTBackend('matched_pyfftw','c2c',True)):
            pyfftw.forget_wisdom()
            spectra=[np.fft.fftshift(backend.fft2(a.astype(float)/255)) for a in inputs]
            amps=[np.hypot(z.real,z.imag) for z in spectra]
            target=np.mean(amps,axis=0); reftarget=np.mean(cells(reference['amplitudes']),axis=0)
            source=[]
            for k,(a,b) in enumerate(zip(spectra,cells(reference['spectra']))):
                phase_diff=np.abs(np.angle(np.exp(1j*(np.angle(a)-cells(reference['phases'])[k]))))
                source.append(dict(source=k+1,fft=delta(a,b),magnitude=delta(amps[k],cells(reference['amplitudes'])[k]),
                    max_phase_radians=float(phase_diff.max()),conditioning=characterize(amps[k])))
            intermediate=dict(fixture=name,runtime=backend.name,sources=source,target=delta(target,reftarget),replays=[])
            with use_backend(backend):
                for op,module,func in [('sf',sf,sf.sf_match),('spec',spec,spec.spec_match)]:
                    for option in (0,1,2):
                        actual=func(inputs,option)
                        ref=cells(cells(expected[op+'_outputs'])[option])
                        for k,(a,b) in enumerate(zip(actual,ref)):
                            d=np.abs(a.astype(np.int16)-b.astype(np.int16))
                            vals,counts=np.unique(d[d!=0],return_counts=True)
                            records.append(dict(fixture=name,kind=group['kind'],screen_pass=oldscreen['passes'],runtime=backend.name,
                                operation=op,option=option,source=k+1,**delta(a,b),
                                nonzero_distribution={str(v):int(c) for v,c in zip(vals,counts)}))
                        if any(not np.array_equal(a,b) for a,b in zip(actual,ref)):
                            pairs=iter(zip(cells(reference['phases']),cells(reference['amplitudes'])))
                            with patch.object(module,'_decompose',lambda a:next(pairs)):
                                replay=func(inputs,option)
                            intermediate['replays'].append(dict(operation=op,option=option,
                                octave_forward_injection=[delta(a,b) for a,b in zip(replay,ref)]))
            intermediates.append(intermediate)
        print(name,'complete',flush=True)
    summary={}
    for runtime in ('numpy','matched_pyfftw'):
        for kind in ('synthetic_candidate','natural_sample'):
            subset=[r for r in records if r['runtime']==runtime and r['kind']==kind]
            summary[runtime+'/'+kind]=summarize(subset)
    report=dict(summary=summary,intermediates=intermediates,comparisons=records,
        conditioning_sha256=hashlib.sha256((ROOT/'conditioning.json').read_bytes()).hexdigest(),
        input_sha256=manifest['input_sha256'],
        reference_output_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in CACHE.glob('*_outputs.mat')})
    (ROOT/'results.json').write_text(json.dumps(report,separators=(',',':'))+'\n', newline='\n')
    write_csv(ROOT/'output_comparisons.csv',[{**r,'nonzero_distribution':json.dumps(r['nonzero_distribution'])} for r in records])
    print(json.dumps(summary,indent=2))


if __name__=='__main__': run()
