"""Non-destructive full-resolution workflow smoke on the three nominated cats."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch

import numpy as np
from shine_color import batch, io, pipeline

ROOT=Path(__file__).resolve().parents[1]


def check():
    corpus=json.loads((ROOT/'reference/backend_policy/corpus_manifest.json').read_text())
    group=next(g for g in corpus['groups'] if g['name']=='cats_green_stride1')
    paths=[ROOT.parent/'SHINE_color_fork/toolbox/SHINE_color_INPUT/samples'/f'cat{i}.jpg' for i in (1,2,3)]
    source_hashes=[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
    assert source_hashes==[s['sha256'] for s in group['sources']]
    calls=[]; original=pipeline.run
    def capture(images,*args,**kwargs):
        output=original(images,*args,**kwargs)
        calls.append((len(images),output))
        return output
    cache=ROOT/'reference/.cache'; cache.mkdir(exist_ok=True)
    folder=Path(tempfile.mkdtemp(prefix='file-workflow-',dir=cache))
    try:
        # Temporary cleanup is confined to the workspace cache.
        assert Path(folder).resolve().parent==cache.resolve()
        with patch.object(pipeline,'run',capture):
            result=batch.process_files(paths,Path(folder)/'outputs','HSV',1)
        assert len(calls)==1 and calls[0][0]==3
        manifest=json.loads(result.manifest_path.read_text(encoding='utf-8'))
        assert manifest==result.manifest
        for a,path,record in zip(calls[0][1],result.output_paths,manifest['outputs']):
            assert a.dtype==np.uint8 and a.shape==(1200,1200,3)
            np.testing.assert_array_equal(io.load_rgb(path),a)
            assert record['pixel_sha256']==io.pixel_sha256(a)
            assert record['file_sha256']==hashlib.sha256(path.read_bytes()).hexdigest()
        assert source_hashes==[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
        report=dict(scope='file workflow on the three previously nominated sample photographs; not experimental stimuli',
            pipeline_calls=len(calls),images_per_call=calls[0][0],
            dimensions=[1200,1200],output_dtype='uint8',output_format='PNG',
            saved_vs_returned_unequal=0,source_files_unchanged=True,
            manifest_verified=True,temporary_outputs_removed=True,manifest=manifest)
    finally:
        assert folder.resolve().parent==cache.resolve()
        io._retry_sharing_violation(lambda: shutil.rmtree(folder))
    (ROOT/'reference/file_workflow_smoke.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k!='manifest'},indent=2))


if __name__=='__main__': check()
