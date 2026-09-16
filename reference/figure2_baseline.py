"""Baseline-only Figure 2 gate: never normalize when originals disagree.

Writes local image artifacts only to an explicitly supplied fresh directory.
The compact evidence contains intensity counts, not spatial image arrays.
"""
import csv
import hashlib
import json
from pathlib import Path
import platform
import subprocess

import numpy as np
from shine_color import color, io
from shine_color.numeric import imhist256, sample_std

PRINTED = ((172.47, 44.72), (80.34, 127.26), (127.26, 76.76))


def histogram_statistics(counts):
    counts = np.asarray(counts, dtype=np.int64)
    if counts.shape != (256,) or np.any(counts < 0) or counts.sum() < 2:
        raise ValueError('expected 256 nonnegative counts and at least two pixels')
    levels = np.arange(256, dtype=np.float64)
    n = int(counts.sum())
    mean = float(np.dot(levels, counts) / n)
    sd = float(np.sqrt(np.dot((levels-mean)**2, counts) / (n-1)))
    return mean, sd


def baseline(samples, destination, octave=None, toolbox=None):
    samples, destination = Path(samples).resolve(), Path(destination).resolve()
    if destination == samples or samples in destination.parents:
        raise ValueError('output must be outside sample directory')
    destination.mkdir(parents=True, exist_ok=False)
    rows = []; originals = []
    for k, printed in enumerate(PRINTED, 1):
        path = samples / f'cat{k}.jpg'
        rgb, metadata = io._read_rgb(path)
        v = color.split_hsv(rgb)[2]
        assert np.array_equal(v, rgb.max(axis=2))
        mean, sd = float(v.mean()), sample_std(v)
        counts = imhist256(v).astype(np.int64)
        np.testing.assert_allclose(histogram_statistics(counts), (mean, sd), atol=1e-12, rtol=0)
        n=v.size
        rows.append(dict(name=path.name, file_sha256=metadata['file_sha256'],
            pixel_sha256=metadata['pixel_sha256'], dimensions=metadata['dimensions'],
            mean=mean, sample_sd=sd, population_sd=float(v.std()),
            rounded=[f'{mean:.2f}', f'{sd:.2f}'], printed=list(printed),
            matches_printed=[f'{mean:.2f}'==f'{printed[0]:.2f}', f'{sd:.2f}'==f'{printed[1]:.2f}'],
            maximum_possible_sample_sd_at_observed_mean=float(np.sqrt(n/(n-1)*mean*(255-mean))),
            histogram=counts.tolist(), preprocessing='validated decode; no EXIF rotation, resizing, cropping or color management',
            v_equals_rgb_channel_max=True))
        originals.append(rgb)
        io.save_rgb(rgb, destination/f'decoded_cat{k}.png')
    evidence = dict(schema_version=1, classification='baseline_mismatch_stop',
        settings=dict(colorspace='HSV',mode=2,iterations=1,rescale_option=1,
                      rescale_note='ignored by mode 2',group_size=3,tie_breaking='unseeded; not executed'),
        baseline_matches=all(all(r['matches_printed']) for r in rows),
        normalization_executed=False, post_histograms=None, post_statistics=None,
        source_reference_commit='870e058fe8bf1e4090baf2401ff0e127d1c0237a',
        software=dict(git_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                      python=platform.python_version(), numpy=np.__version__), sources=rows)
    if octave:
        from scipy.io import loadmat
        def q(value): return "'"+str(value).replace('\\','/').replace("'","''")+"'"
        harness=Path(__file__).parent/'octave'
        expression=f'addpath({q(harness.resolve())}); probe_figure2_baseline({q(Path(toolbox).resolve())},{q(samples)},{q(destination)});'
        process=subprocess.run([str(octave),'--quiet','--no-gui','--eval',expression],capture_output=True,text=True,check=True)
        (destination/'octave_log.txt').write_text(process.stdout+process.stderr,encoding='utf-8')
        result=loadmat(destination/'octave_baseline.mat')
        evidence['octave']=dict(version=str(result['octave_version'].item()),
            common_decoded_histograms=result['common_histograms'].T.astype(int).tolist(),
            source_jpeg_decoded_unequal=result['decoded_unequal'].ravel().astype(int).tolist(),
            original_statistics=result['statistics'].tolist(),
            common_decoded_statistics=result['common_statistics'].tolist(),
            jpeg_histograms_equal=[bool(np.array_equal(result['histograms'][:,i],r['histogram'])) for i,r in enumerate(rows)],
            common_decoded_histograms_equal=[bool(np.array_equal(result['common_histograms'][:,i],r['histogram'])) for i,r in enumerate(rows)])
    (destination/'figure2_reproduction_metrics.json').write_text(json.dumps(evidence,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    with (destination/'figure2_reproduction_histograms.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f); writer.writerow(['source_name','source_file_sha256','stage','intensity','pixel_count'])
        for row in rows:
            writer.writerows((row['name'],row['file_sha256'],'original',i,c) for i,c in enumerate(row['histogram']))
    # Diagnostic visualization explicitly marks the stop; never fabricate post panels.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes=plt.subplots(3,3,figsize=(13,10),gridspec_kw={'width_ratios':[1,1.5,1.3]})
    for i,(row,rgb) in enumerate(zip(rows,originals)):
        axes[i,0].imshow(rgb); axes[i,0].set_title(row['name']); axes[i,0].axis('off')
        axes[i,1].bar(np.arange(256),row['histogram'],width=1,color='#315d79')
        axes[i,1].set(xlim=(0,255),xlabel='Working V (0-255)',ylabel='Pixel count',
                      title=f"Calculated M = {row['mean']:.2f}, SD = {row['sample_sd']:.2f}")
        axes[i,2].axis('off')
        axes[i,2].text(0,.8,f"Printed M = {row['printed'][0]:.2f}\nPrinted SD = {row['printed'][1]:.2f}\n\nMean match: {row['matches_printed'][0]}\nSD match: {row['matches_printed'][1]}\n\nPost-match: NOT RUN",va='top',fontsize=12)
    fig.suptitle('SHINE_color_py Figure 2 baseline diagnostic\nOriginal-statistic mismatch: reproduction paused',fontsize=17)
    fig.text(.06,.018,'Exact upstream JPEGs; HSV working V; sample SD. No normalization or RNG seeding.\nFull source hashes and software commit: figure2_reproduction_metrics.json',fontsize=10)
    fig.tight_layout(rect=(0,.06,1,.93)); fig.savefig(destination/'figure2_baseline_diagnostic.png',dpi=150); plt.close(fig)
    # Verify source bytes still match the frozen baseline.
    assert all(hashlib.sha256((samples/r['name']).read_bytes()).hexdigest()==r['file_sha256'] for r in rows)
    return evidence
