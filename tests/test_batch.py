"""Group semantics, pixel equivalence, provenance and publication failures."""
import hashlib
import json
import os

import numpy as np
from PIL import Image
import pytest
from shine_color import batch, histogram, io, pipeline, __version__


@pytest.fixture
def files(tmp_path):
    source=tmp_path/'source'; source.mkdir()
    rng=np.random.default_rng(520)
    paths=[]
    for name in ('zeta.png','Alpha.png','beta.png'):
        a=rng.integers(0,256,(13,17,3),dtype=np.uint8)
        path=source/name; io.save_rgb(a,path); paths.append(path)
    return paths


def snapshot(directory):
    return {p.name:p.read_bytes() for p in directory.iterdir() if p.is_file()}


def test_calls_pipeline_once_with_entire_ordered_group(files,tmp_path,monkeypatch):
    calls=[]; original=pipeline.run
    def observe(images,*args,**kwargs):
        calls.append((images,args,kwargs))
        return original(images,*args,**kwargs)
    monkeypatch.setattr(pipeline,'run',observe)
    result=batch.process_files(files,tmp_path/'out','RGB',1)
    assert len(calls)==1 and len(calls[0][0])==3
    for image,path in zip(calls[0][0],files): np.testing.assert_array_equal(image,io.load_rgb(path))
    assert [p.name for p in result.output_paths]==[p.name for p in files]
    assert result.manifest['group']['ordered_input_names']==[p.name for p in files]


@pytest.mark.parametrize('space,mode,iterations,option',[
    ('RGB',1,1,1),('HSV',3,2,0),('Lab',4,1,2),
    ('RGB',5,2,1),('HSV',6,2,0),('Lab',7,2,2),('RGB',8,2,1)])
def test_batch_equals_direct_and_source_bytes_unchanged(files,tmp_path,monkeypatch,space,mode,iterations,option):
    before=[p.read_bytes() for p in files]
    images=[io.load_rgb(p) for p in files]
    original=histogram.hist_match
    rng=np.random.default_rng(912)
    monkeypatch.setattr(histogram,'hist_match',lambda a,rng=None:original(a,rng=controlled))
    controlled=rng
    expected=pipeline.run(images,space,mode,iterations,option)
    controlled=np.random.default_rng(912)  # Scoped test control, not public behavior.
    result=batch.process_files(files,tmp_path/'out',space,mode,iterations,option)
    for path,a in zip(result.output_paths,expected): np.testing.assert_array_equal(io.load_rgb(path),a)
    assert [p.read_bytes() for p in files]==before


def test_directory_is_sorted_nonrecursive_ignores_unsupported_and_output(files,tmp_path):
    source=files[0].parent; output=source/'processed'
    output.mkdir(); io.save_rgb(io.load_rgb(files[0]),output/'old.png')
    (source/'notes.txt').write_text('not an image')
    result=batch.process_directory(source,output,'RGB',1)
    assert result.manifest['group']['ordered_input_names']==['Alpha.png','beta.png','zeta.png']
    assert result.manifest['group']['count']==3 and (output/'old.png').exists()
    with pytest.raises(ValueError,match='must differ'): batch.process_directory(source,source,'RGB',1,overwrite=True)


@pytest.mark.parametrize('cause',['dimensions','bad_content','stem_collision','case_collision','duplicate','missing','one','unordered'])
def test_invalid_group_fails_without_writes_or_processing(files,tmp_path,monkeypatch,cause):
    output=tmp_path/'out'; inputs=files.copy()
    if cause=='dimensions': Image.new('RGB',(2,3)).save(inputs[1])
    elif cause=='bad_content': inputs[1].write_text('bad PNG')
    elif cause=='stem_collision':
        path=files[0].with_suffix('.jpg'); Image.fromarray(io.load_rgb(files[0])).save(path); inputs[1]=path
    elif cause=='case_collision':
        path=tmp_path/'elsewhere'; path.mkdir()
        target=path/'ZETA.png'; io.save_rgb(io.load_rgb(files[0]),target); inputs[1]=target
    elif cause=='duplicate': inputs[1]=inputs[0]
    elif cause=='missing': inputs[1]=tmp_path/'absent.png'
    elif cause=='one': inputs=files[:1]
    elif cause=='unordered': inputs=set(files)
    def unexpected(*a,**k): pytest.fail('invalid group reached pipeline')
    monkeypatch.setattr(pipeline,'run',unexpected)
    with pytest.raises((ValueError,TypeError,OSError)): batch.process_files(inputs,output,'RGB',1)
    assert not output.exists()


@pytest.mark.parametrize('name',['zeta.png','manifest.json','ALPHA.PNG'])
def test_collision_preflight_preserves_every_destination(files,tmp_path,monkeypatch,name):
    output=tmp_path/'out'; output.mkdir(); (output/name).write_bytes(b'precious old file')
    before=snapshot(output)
    monkeypatch.setattr(pipeline,'run',lambda *a,**k:pytest.fail('collision reached pipeline'))
    with pytest.raises(FileExistsError): batch.process_files(files,output,'RGB',1)
    assert snapshot(output)==before and len(list(output.iterdir()))==1


def test_overwrite_is_explicit_and_recorded(files,tmp_path):
    output=tmp_path/'out'
    first=batch.process_files(files,output,'RGB',1)
    (output/'unrelated.txt').write_text('keep')
    second=batch.process_files(files,output,'HSV',3,overwrite=True)
    assert first.manifest['overwrite'] is False and second.manifest['overwrite'] is True
    assert (output/'unrelated.txt').read_text()=='keep'
    assert second.manifest['pipeline']['colorspace']=='HSV'


def test_inputs_never_overwritten_even_with_opt_in(files):
    before=[p.read_bytes() for p in files]
    with pytest.raises(ValueError,match='input file'):
        batch.process_files(files,files[0].parent,'RGB',1,overwrite=True)
    assert [p.read_bytes() for p in files]==before


def test_hard_link_input_alias_protected(files,tmp_path):
    output=tmp_path/'out'; output.mkdir(); os.link(files[1],output/'zeta.png')
    before=[p.read_bytes() for p in files]
    with pytest.raises(ValueError,match='input file'): batch.process_files(files,output,'RGB',1,overwrite=True)
    assert [p.read_bytes() for p in files]==before


@pytest.mark.parametrize('mode,randomness,ops',[(1,'not_applicable',['lum_match']),
    (2,'stochastic_unseeded',['hist_match']),(5,'stochastic_unseeded',['hist_match','sf_match']),
    (8,'stochastic_unseeded',['spec_match','hist_match'])])
def test_manifest_and_hashes(files,tmp_path,mode,randomness,ops):
    result=batch.process_files(files,tmp_path/'out','lab',mode,iterations=2,rescale_option=0)
    m=json.loads(result.manifest_path.read_text(encoding='utf-8'))
    assert m==result.manifest and m['schema_version']==1
    assert m['software']['version']==__version__=='0.1.0.dev0'
    for key in ('python','numpy','pillow','implementation_sha256'): assert m['software'][key]
    assert m['pipeline']==dict(colorspace='CIELab',mode=mode,ordered_mode_operations=ops,iterations=2,rescale_option=0)
    assert m['histogram_tie_breaking']==randomness and 'seed' not in m
    assert m['processing_started_utc']<=m['processing_completed_utc']
    assert m['group']['count']==3 and m['group']['ordering']=='provided_sequence'
    assert m['io_policy']['output_metadata']=='none'
    for key,paths in [('inputs',files),('outputs',result.output_paths)]:
        for record,path in zip(m[key],paths):
            data=path.read_bytes(); a=io.load_rgb(path)
            assert record['file_sha256']==hashlib.sha256(data).hexdigest()
            assert record['size_bytes']==len(data)
            assert record['pixel_sha256']==hashlib.sha256(a.tobytes(order='C')).hexdigest()
            assert record['dimensions']==[17,13]
    assert str(tmp_path) not in result.manifest_path.read_text(encoding='utf-8')


@pytest.mark.parametrize('point',['pipeline','staging','publish_second','manifest'])
@pytest.mark.parametrize('overwrite',[False,True])
def test_failures_leave_no_new_success_and_restore_existing(files,tmp_path,monkeypatch,point,overwrite):
    output=tmp_path/'out'; output.mkdir()
    if overwrite: batch.process_files(files,output,'RGB',1)
    (output/'unrelated.txt').write_text('preserved')
    before=snapshot(output); inputs_before=[p.read_bytes() for p in files]
    if point=='pipeline':
        def fail(*a,**k): raise RuntimeError('injected pipeline failure')
        monkeypatch.setattr(pipeline,'run',fail)
    elif point=='staging':
        original=io.save_rgb; counter=0
        def fail(a,p,**k):
            nonlocal counter
            counter+=1
            if counter==2: raise OSError('injected staging failure')
            return original(a,p,**k)
        monkeypatch.setattr(io,'save_rgb',fail)
    else:
        original=io._publish_file
        def fail(staged,destination,overwrite):
            if destination.parent==output and destination.name==('Alpha.png' if point=='publish_second' else 'manifest.json'):
                raise OSError('injected publication failure')
            return original(staged,destination,overwrite)
        monkeypatch.setattr(io,'_publish_file',fail)
    with pytest.raises((RuntimeError,OSError)): batch.process_files(files,output,'HSV',3,overwrite=overwrite)
    assert snapshot(output)==before
    assert {p.name for p in output.iterdir()}==set(before)
    assert [p.read_bytes() for p in files]==inputs_before


def test_existing_lock_is_never_removed(files,tmp_path):
    output=tmp_path/'out'; output.mkdir(); lock=output/'.shine-color.lock'; lock.mkdir()
    with pytest.raises(FileExistsError,match='locked'): batch.process_files(files,output,'RGB',1)
    assert lock.is_dir() and not (output/'manifest.json').exists()


def test_manifest_published_last(files,tmp_path,monkeypatch):
    output=tmp_path/'out'; order=[]; original=io._publish_file
    def observe(staged,destination,overwrite):
        if destination.parent==output:
            order.append(destination.name)
            assert not (output/'manifest.json').exists()
            if destination.name=='manifest.json':
                assert all((output/p.name).exists() for p in files)
        return original(staged,destination,overwrite)
    monkeypatch.setattr(io,'_publish_file',observe)
    batch.process_files(files,output,'RGB',1)
    assert order==[p.name for p in files]+['manifest.json']


def test_no_clobber_publication_race(files,tmp_path,monkeypatch):
    output=tmp_path/'out'; original=io._publish_file
    def race(staged,destination,overwrite):
        if destination.parent==output and destination.name=='Alpha.png':
            destination.write_bytes(b'external concurrent file')
        return original(staged,destination,overwrite)
    monkeypatch.setattr(io,'_publish_file',race)
    with pytest.raises(FileExistsError): batch.process_files(files,output,'RGB',1)
    assert snapshot(output)=={'Alpha.png':b'external concurrent file'}


@pytest.mark.parametrize('late_name',['manifest.json','zeta.png'])
def test_late_collision_during_staging_preserves_foreign_file(files,tmp_path,monkeypatch,late_name):
    output=tmp_path/'out'; save=io.save_rgb
    def arrive(image,path,**kwargs):
        result=save(image,path,**kwargs)
        if path.name=='beta.png': (output/late_name).write_bytes(b'late external file')
        return result
    monkeypatch.setattr(io,'save_rgb',arrive)
    with pytest.raises(FileExistsError): batch.process_files(files,output,'RGB',1)
    assert snapshot(output)=={late_name:b'late external file'}
    assert len(list(output.iterdir()))==1


def test_failed_rollback_retains_recovery_without_success_manifest(files,tmp_path,monkeypatch):
    output=tmp_path/'out'; batch.process_files(files,output,'RGB',1)
    before=snapshot(output)
    publish=io._publish_file; replace=os.replace
    def fail_publication(staged,destination,overwrite):
        if destination.parent==output and destination.name=='manifest.json':
            raise OSError('injected manifest failure')
        return publish(staged,destination,overwrite)
    def fail_restore(source,destination):
        if source.parent.name=='backup' and destination.name=='zeta.png':
            raise OSError('injected rollback failure')
        return replace(source,destination)
    monkeypatch.setattr(io,'_publish_file',fail_publication)
    monkeypatch.setattr(os,'replace',fail_restore)
    with pytest.raises(batch.BatchRecoveryError,match='Rollback incomplete'):
        batch.process_files(files,output,'HSV',3,overwrite=True)
    assert not (output/'manifest.json').exists()
    assert (output/'.shine-color.lock').is_dir()
    recovery=list(output.glob('.shine-stage-*'))
    assert len(recovery)==1
    assert (recovery[0]/'backup/zeta.png').read_bytes()==before['zeta.png']
    assert (recovery[0]/'backup/manifest.json').read_bytes()==before['manifest.json']


@pytest.mark.parametrize('persistent',[False,True])
def test_windows_cleanup_sharing_violation(files,tmp_path,monkeypatch,persistent):
    output=tmp_path/'out'; remove=batch.shutil.rmtree; attempts=[]
    def sharing(path,*args,**kwargs):
        if path.name.startswith('.shine-stage-'):
            attempts.append(path)
            if persistent or len(attempts)==1:
                error=PermissionError('injected Windows sharing violation'); error.winerror=32
                raise error
        return remove(path,*args,**kwargs)
    with monkeypatch.context() as scoped:
        scoped.setattr(batch.shutil,'rmtree',sharing)
        scoped.setattr(io.time,'sleep',lambda delay:None)
        if persistent:
            with pytest.raises(PermissionError): batch.process_files(files,output,'RGB',1)
        else: batch.process_files(files,output,'RGB',1)
    assert len(attempts)==(7 if persistent else 2)
    assert (output/'.shine-color.lock').exists()==persistent
    # Processing/publication succeeded; a persistent failure is cleanup-only.
    manifest=json.loads((output/'manifest.json').read_text())
    for record in manifest['outputs']:
        assert hashlib.sha256((output/record['filename']).read_bytes()).hexdigest()==record['file_sha256']


@pytest.mark.parametrize('bad', [dict(colorspace='bad'),dict(mode=9),dict(iterations=0),dict(rescale_option=4),dict(overwrite='yes')])
def test_bad_parameters_write_nothing(files,tmp_path,bad):
    kwargs=dict(colorspace='RGB',mode=1); kwargs.update(bad)
    with pytest.raises((ValueError,TypeError)): batch.process_files(files,tmp_path/'out',**kwargs)
    assert not (tmp_path/'out').exists()
