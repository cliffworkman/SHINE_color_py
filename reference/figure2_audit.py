"""Reviewed Figure 2 audit: isolate JPEG decode from common-array histMatch.

No algorithm replacement, RNG seeding, network, or source-image mutation.
Spatial arrays and rendered figures stay in a fresh ignored artifact directory.
"""
import csv
import hashlib
import json
from pathlib import Path
import subprocess
from unittest.mock import patch

import numpy as np
from scipy.io import loadmat, savemat
from shine_color import batch, color, histogram, io, pipeline
from shine_color.numeric import imhist256, sample_std
from .figure2_baseline import PRINTED


def cells(items):
    result=np.empty((1,len(items)),dtype=object)
    for i,item in enumerate(items): result[0,i]=item
    return result


def summary(images):
    return dict(histograms=[imhist256(a).astype(int).tolist() for a in images],
                statistics=[[float(a.mean()),sample_std(a)] for a in images])


def _quote(path):
    return "'"+str(Path(path).resolve()).replace('\\','/').replace("'","''")+"'"


def _octave(executable, expression, log):
    harness=Path(__file__).parent/'octave'
    result=subprocess.run([str(executable),'--quiet','--no-gui','--eval',
        f'addpath({_quote(harness)}); '+expression],capture_output=True,text=True,check=True)
    Path(log).write_text(result.stdout+result.stderr,encoding='utf-8')


def _reference(executable, toolbox, source, destination):
    _octave(executable,f'export_figure2_common({_quote(toolbox)},{_quote(source)},{_quote(destination)});',
            Path(destination).with_suffix('.log'))
    data=loadmat(destination)
    record=dict(pre=dict(histograms=data['pre_hist'].T.astype(int).tolist(),statistics=data['pre_stats'].tolist()),
                target=data['target'].ravel().astype(int).tolist(),
                post=dict(histograms=data['post_hist'].T.astype(int).tolist(),statistics=data['post_stats'].tolist()),
                version=str(data['octave_version'].item()))
    return record,[a.ravel().astype(np.uint8) for a in data['sorted_post'].ravel()]


def _python(images, call):
    captured={}; original=histogram.hist_match
    def capture(inputs,*args,**kwargs):
        if captured: raise AssertionError('expected exactly one histogram stage')
        output=original(inputs,*args,**kwargs)
        captured.update(pre=summary(inputs),target=histogram.average_histogram(inputs).tolist(),
                        post=summary(output),sorted_values=[np.sort(a.ravel()) for a in output])
        return output
    hashes=[io.pixel_sha256(a) for a in images]
    with patch.object(histogram,'hist_match',capture):
        output=call()
    assert hashes==[io.pixel_sha256(a) for a in images]
    return captured,output


def compare_records(python, reference, python_sorted, reference_sorted):
    """Exact count/ordering contract; descriptive floating reductions stay separate."""
    result=dict(pre_histograms_equal=python['pre']['histograms']==reference['pre']['histograms'],
        target_histogram_equal=python['target']==reference['target'],
        post_histograms_equal=python['post']['histograms']==reference['post']['histograms'],
        within_python_post_equal=all(h==python['post']['histograms'][0] for h in python['post']['histograms']),
        within_reference_post_equal=all(h==reference['post']['histograms'][0] for h in reference['post']['histograms']),
        sorted_values_equal=[bool(np.array_equal(a,b)) for a,b in zip(python_sorted,reference_sorted)],
        max_abs_post_statistic_difference=float(np.max(np.abs(np.array(python['post']['statistics'])-reference['post']['statistics']))))
    checks=[result[k] for k in ('pre_histograms_equal','target_histogram_equal','post_histograms_equal',
                               'within_python_post_equal','within_reference_post_equal')]
    result['passes']=all(checks) and len(python_sorted)==len(reference_sorted)==3 and all(result['sorted_values_equal'])
    return result


def run(samples, destination, octave, toolbox, historical_toolbox=None):
    samples=Path(samples).resolve(); destination=Path(destination).resolve()
    if destination==samples or samples in destination.parents: raise ValueError('output must be outside samples')
    destination.mkdir(parents=True,exist_ok=False)
    inputs=[samples/f'cat{k}.jpg' for k in (1,2,3)]
    decoded=[io._read_rgb(p) for p in inputs]; pillow=[a for a,_ in decoded]
    source_hashes=[m['file_sha256'] for _,m in decoded]
    frozen=json.loads((Path(__file__).resolve().parents[1]/'tests/reference/fixtures/figure2_baseline.json').read_text())
    assert source_hashes==[s['file_sha256'] for s in frozen['sources']]
    savemat(destination/'pillow_rgb.mat',dict(rgb=cells(pillow)),do_compression=True)
    _octave(octave,f'export_figure2_decode({_quote(samples)},{_quote(destination/"octave_rgb.mat")});',destination/'decode.log')
    decoded_octave=[a for a in loadmat(destination/'octave_rgb.mat')['rgb'].ravel()]
    decoders=[]
    for k,(a,b) in enumerate(zip(pillow,decoded_octave)):
        assert a.shape==b.shape and a.dtype==b.dtype==np.uint8
        diff=a.astype(np.int16)-b.astype(np.int16)
        va=color.split_hsv(a)[2]; vb=color.split_hsv(b)[2]
        decoders.append(dict(name=inputs[k].name,source_file_sha256=source_hashes[k],dimensions=[a.shape[1],a.shape[0]],
            unequal_rgb_scalars=int(np.count_nonzero(diff)),total_rgb_scalars=int(diff.size),
            unequal_percent=float(100*np.count_nonzero(diff)/diff.size),max_abs_channel_difference=int(np.abs(diff).max()),
            mean_abs_channel_difference=float(np.abs(diff).mean()),pillow_pixel_sha256=io.pixel_sha256(a),
            octave_pixel_sha256=io.pixel_sha256(b),pillow_working_v=summary([va])['statistics'][0],
            octave_working_v_using_same_python_hsv=summary([vb])['statistics'][0]))
    report=dict(schema_version=1,scope='exact count and sorted-value parity on common pixels; publication labels are secondary',
        baseline_commit='a4f832fbc858374de2ec75cd9cc1a6995a36ff4f',software=batch._software(),
        reference_commit='870e058fe8bf1e4090baf2401ff0e127d1c0237a',
        historical_commit='330a9be6e49f59e5d68fb985744b2a50c278e8d8' if historical_toolbox else None,
        settings=dict(colorspace='HSV',mode=2,iterations=1,rescale_option=1,rescale_ignored=True,group_size=3,ties='stochastic_unseeded'),
        source_jpeg_paths=[str(p) for p in inputs],decoders=decoders,paths={})
    plot_images={}
    for name,images in [('pillow',pillow),('octave',decoded_octave)]:
        folder=destination/name; folder.mkdir(); lossless=folder/'inputs'; lossless.mkdir()
        for k,a in enumerate(images,1):
            io.save_rgb(a,lossless/f'cat{k}.png')
            assert np.array_equal(io.load_rgb(lossless/f'cat{k}.png'),a)
        python,outputs=_python(images,lambda: pipeline.run(images,'HSV',2,1,1))
        reference,reference_sorted=_reference(octave,toolbox,destination/f'{name}_rgb.mat',folder/'reference.mat')
        python_sorted=python.pop('sorted_values')
        comparison=compare_records(python,reference,python_sorted,reference_sorted)
        record=dict(python=python,octave=reference,comparison=comparison,
            common_input_pixel_sha256=[io.pixel_sha256(a) for a in images],
            sorted_post_sha256=[hashlib.sha256(a.tobytes()).hexdigest() for a in python_sorted])
        report['paths'][name]=record
        if not comparison['passes']:
            _write_json(destination/'failure.json',report)
            raise RuntimeError('Unexpected identical-array mismatch; stop without changing algorithms')
        # Independent file API run, same pixels, separate stochastic realization.
        file_record,file_result=_python(images,lambda: batch.process_files(
            [lossless/f'cat{k}.png' for k in (1,2,3)],folder/'batch_outputs','HSV',2,1,1,overwrite=False))
        file_record.pop('sorted_values')
        assert all(file_record[k]==python[k] for k in ('target',))
        assert file_record['pre']['histograms']==python['pre']['histograms']
        assert file_record['post']['histograms']==python['post']['histograms']
        record['batch_histograms_equal']=True
        record['batch_manifest_relative_path']=file_result.manifest_path.relative_to(destination).as_posix()
        record['batch_output_pixel_sha256']=[r['pixel_sha256'] for r in file_result.manifest['outputs']]
        for k,a in enumerate(outputs,1): io.save_rgb(a,folder/f'python_cat{k}.png')
        if historical_toolbox:
            old,old_sorted=_reference(octave,historical_toolbox,destination/f'{name}_rgb.mat',folder/'historical.mat')
            record['historical']=old
            record['historical_comparison']=compare_records(python,old,python_sorted,old_sorted)
            if not record['historical_comparison']['passes']:
                _write_json(destination/'failure.json',report)
                raise RuntimeError('Historical algorithm discrepancy: stop for review')
        for runtime in ('python','octave'):
            record[runtime]['post']['rounded']=[[f'{m:.2f}',f'{s:.2f}'] for m,s in record[runtime]['post']['statistics']]
            record[runtime]['post']['published_label_agreement']=[pair==['126.69','74.77'] for pair in record[runtime]['post']['rounded']]
        plot_images[name]=(images,outputs)
    assert source_hashes==[hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs]
    report['sources_unchanged']=True
    _write_json(destination/'figure2_reproduction_metrics.json',report)
    with (destination/'figure2_reproduction_histograms.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f);writer.writerow(['path','runtime','stage','source','source_file_sha256','decoded_pixel_sha256','bin','count'])
        for name,record in report['paths'].items():
            for runtime in ('python','octave','historical'):
                if runtime not in record: continue
                for stage in ('pre','post'):
                    for i,h in enumerate(record[runtime][stage]['histograms']):
                        writer.writerows((name,runtime,stage,inputs[i].name,source_hashes[i],record['common_input_pixel_sha256'][i],b,c) for b,c in enumerate(h))
                writer.writerows((name,runtime,'target','three-cat group',';'.join(source_hashes),';'.join(record['common_input_pixel_sha256']),b,c) for b,c in enumerate(record[runtime]['target']))
    render(report,plot_images,destination/'figure2_reproduction.png')
    return report


def _write_json(path,value):
    Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def numerical_evidence(report):
    """Nonspatial counts/statistics only; no RGB arrays, source paths or assets."""
    return dict(schema_version=report['schema_version'],
        scope='Nonspatial intensity counts, statistics and hashes; no image pixel arrangement',
        baseline_commit=report['baseline_commit'],reference_commit=report['reference_commit'],
        historical_commit=report['historical_commit'],settings=report['settings'],
        decoders=report['decoders'],paths=report['paths'])


def render(report,images,path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(3,5,figsize=(19,11),gridspec_kw={'width_ratios':[1,1.15,1.7,1.7,1]})
    for i in range(3):
        axes[i,0].imshow(images['pillow'][0][i]);axes[i,0].axis('off');axes[i,0].set_title(f'cat{i+1}.jpg\nPillow-decoded original')
        axes[i,1].axis('off')
        d=report['decoders'][i]
        axes[i,1].text(0,.98,f'PRINTED BASELINE\nM {PRINTED[i][0]:.2f} / SD {PRINTED[i][1]:.2f}\n'+
            ('Pillow matches: M + SD\n' if i==2 else ('Pillow mismatch: SD\n' if i==1 else 'Pillow mismatch: M + SD\n'))+
            ('SD inconsistent with mean\nand 0-255 range\n' if i==1 else '')+
            f"\nSUPPLIED SOURCE\nPillow: {d['pillow_working_v'][0]:.5f}\nSD {d['pillow_working_v'][1]:.5f}\nOctave: {d['octave_working_v_using_same_python_hsv'][0]:.5f}\nSD {d['octave_working_v_using_same_python_hsv'][1]:.5f}",va='top',fontsize=10)
        for name,c in [('pillow','#176488'),('octave','#bb531c')]:
            r=report['paths'][name]
            axes[i,2].plot(range(256),r['python']['pre']['histograms'][i],color=c,label=name+' decode',linewidth=1)
            axes[i,3].plot(range(256),r['python']['post']['histograms'][i],color=c,label=name+' input; Python',linewidth=1)
            axes[i,3].plot(range(256),r['octave']['post']['histograms'][i],color=c,linestyle='--',linewidth=.7)
        axes[i,2].set_title('Original working-V histograms')
        pa=report['paths']['pillow']['python']['post']['rounded'][i]
        pb=report['paths']['octave']['python']['post']['rounded'][i]
        axes[i,3].set_title(f'Post histMatch: exact Python/Octave counts\nA: {pa[0]} / {pa[1]} | B: {pb[0]} / {pb[1]}',fontsize=10)
        for col in (2,3):
            axes[i,col].set(xlim=(0,255),xlabel='Working V (0-255)',ylabel='Pixel count');axes[i,col].legend(fontsize=8)
        axes[i,4].imshow(images['pillow'][1][i]);axes[i,4].axis('off');axes[i,4].set_title('Python HSV histMatch\nPath A, one realization')
    fig.suptitle('SHINE_color Figure 2 reproduction audit: source, decoder, and algorithmic comparisons',fontsize=17,y=.98)
    post=report['paths']['pillow']['python']['post']['rounded'][0]
    footer=f"HSV mode 2; one iteration; one three-cat group. Printed post target: M 126.69 / SD 74.77. Path A matches; Path B differs (126.70 / 74.78).\nSolid post curves: Python; dashed curves: Octave on IDENTICAL arrays (overlap exactly). Histogram ties are stochastic; RGB pixel identity is not expected.\nPython commit {report['software']['git_commit']}; full exact JPEG/pixel hashes in companion metrics JSON."
    fig.text(.035,.026,footer,fontsize=9)
    fig.tight_layout(rect=(.01,.10,.99,.95));fig.savefig(path,dpi=150);plt.close(fig)
