"""File representation tests before building the batch layer."""
import hashlib
import struct
import zlib

import numpy as np
from PIL import Image, PngImagePlugin
import pytest
from shine_color import io, pipeline


def pixels():
    return np.random.default_rng(519).integers(0, 256, (13, 17, 3), dtype=np.uint8)


def chunk(kind, data):
    return struct.pack('>I', len(data))+kind+data+struct.pack('>I', zlib.crc32(kind+data))


@pytest.mark.parametrize('variant', ['random', 'limits', 'noncontiguous'])
def test_png_exact_roundtrip(tmp_path, variant):
    a = pixels()
    if variant == 'limits': a = np.array([[[0, 1, 127], [128, 254, 255]]], dtype=np.uint8)
    if variant == 'noncontiguous': a = a[::-1, ::2]
    original = a.copy(); path = tmp_path/'image.png'
    assert io.save_rgb(a, path) == path
    b = io.load_rgb(path)
    assert b.dtype == np.uint8 and b.shape == a.shape
    np.testing.assert_array_equal(b, a)
    np.testing.assert_array_equal(a, original)


@pytest.mark.parametrize('mode', ['L', '1', 'P'])
def test_grayscale_and_opaque_palette(tmp_path, mode):
    a = np.arange(16, dtype=np.uint8).reshape(4, 4)*17
    im = Image.fromarray(a)
    if mode == '1': im = im.convert('1')
    if mode == 'P':
        im = Image.fromarray(a, 'P')
        im.putpalette(np.column_stack([np.arange(256),255-np.arange(256),np.arange(256)//2]).astype(np.uint8).ravel())
    path=tmp_path/'a.png'; im.save(path)
    expected = np.array(im.convert('RGB'))
    np.testing.assert_array_equal(io.load_rgb(path), expected)
    if mode != 'P':
        for c in (1, 2): np.testing.assert_array_equal(expected[...,0], expected[...,c])


@pytest.mark.parametrize('mode', ['RGBA', 'LA', 'P', 'RGB', 'L'])
def test_reject_alpha_and_transparency_even_when_opaque(tmp_path, mode):
    im = Image.new(mode, (4, 3)); options={}
    if mode == 'P': options['transparency']=255
    if mode == 'RGB': options['transparency']=(1, 2, 3)
    if mode == 'L': options['transparency']=255
    path=tmp_path/'a.png'; im.save(path, **options)
    with pytest.raises(ValueError, match='Alpha/transparency'): io.load_rgb(path)


@pytest.mark.parametrize('orientation', range(1, 9))
def test_exif_orientation_and_no_stale_tag(tmp_path, orientation):
    a = pixels(); im=Image.fromarray(a); exif=Image.Exif(); exif[274]=orientation
    path=tmp_path/'source.png'; im.save(path, exif=exif)
    transforms={1:lambda x:x,2:lambda x:x[:,::-1],3:lambda x:x[::-1,::-1],
                4:lambda x:x[::-1],5:lambda x:x.transpose(1,0,2),
                6:lambda x:np.rot90(x,-1),7:lambda x:x.transpose(1,0,2)[::-1,::-1],
                8:lambda x:np.rot90(x,1)}
    expected=transforms[orientation](a)
    loaded=io.load_rgb(path); np.testing.assert_array_equal(loaded,expected)
    output=tmp_path/'out.png'; io.save_rgb(loaded,output)
    with Image.open(output) as saved: assert 274 not in saved.getexif()
    np.testing.assert_array_equal(io.load_rgb(output),expected)


def test_jpeg_orientation_uses_decoded_pixels(tmp_path):
    exif=Image.Exif(); exif[274]=6
    path=tmp_path/'a.jpg'; Image.fromarray(pixels()).save(path,exif=exif)
    with Image.open(path) as im: expected=np.rot90(np.array(im),-1)
    np.testing.assert_array_equal(io.load_rgb(path),expected)


@pytest.mark.parametrize('color_type,channels', [(0,1),(2,3),(4,2),(6,4)])
def test_reject_actual_16_bit_png_header(tmp_path,color_type,channels):
    # Include RGB16: Pillow exposes it as mode RGB after silently reducing depth.
    raw=b'\x00'+b'\x80\x01'*channels
    data=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,16,color_type,0,0,0))
    data+=chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')
    path=tmp_path/'scientific.png'; path.write_bytes(data)
    with pytest.raises(ValueError,match='High-bit-depth'): io.load_rgb(path)


@pytest.mark.parametrize('kind', ['gif','tiff','cmyk','animated','mislabeled','invalid_orientation'])
def test_reject_unsupported_inputs(tmp_path,kind):
    im=Image.fromarray(pixels()); path=tmp_path/'a.png'
    if kind in ('gif','tiff'):
        path=tmp_path/('a.'+kind); im.save(path)
    elif kind=='cmyk': path=tmp_path/'a.jpg'; im.convert('CMYK').save(path)
    elif kind=='animated': im.save(path,save_all=True,append_images=[Image.fromarray(255-pixels())],duration=20)
    elif kind=='mislabeled': im.save(path,format='JPEG')
    else:
        exif=Image.Exif(); exif[274]=9; im.save(path,exif=exif)
    with pytest.raises(ValueError): io.load_rgb(path)


def test_icc_gamma_do_not_transform_and_are_not_copied(tmp_path):
    a=pixels(); metadata=PngImagePlugin.PngInfo()
    metadata.add(b'gAMA',struct.pack('>I',45455)); metadata.add_text('Author','not copied')
    path=tmp_path/'source.png'
    Image.fromarray(a).save(path,pnginfo=metadata,icc_profile=b'opaque profile bytes; no CMS')
    b,record=io._read_rgb(path)
    np.testing.assert_array_equal(b,a)
    assert record['icc_profile_present'] and record['gamma_present']
    output=tmp_path/'out.png'; io.save_rgb(b,output)
    with Image.open(output) as im:
        assert not set(im.info)&{'icc_profile','gamma','exif','Author','xmp'}


@pytest.mark.parametrize('space,mode', [('RGB',1),('HSV',3),('Lab',4)])
def test_load_pipeline_save_reload_exact(tmp_path,space,mode):
    inputs=[]
    for i in range(3):
        path=tmp_path/f'in{i}.png'; io.save_rgb(np.roll(pixels(),i,axis=0),path)
        inputs.append(io.load_rgb(path))
    actual=pipeline.run(inputs,space,mode)
    for i,a in enumerate(actual):
        path=tmp_path/f'out{i}.png'; io.save_rgb(a,path)
        np.testing.assert_array_equal(io.load_rgb(path),a)


@pytest.mark.parametrize('bad', [np.zeros((2,2,3)),np.zeros((2,2,3),dtype=np.uint16),np.zeros((2,2),dtype=np.uint8)])
def test_save_rejects_dtype_shape_without_writing(tmp_path,bad):
    with pytest.raises((TypeError,ValueError)): io.save_rgb(bad,tmp_path/'bad.png')
    assert not list(tmp_path.iterdir())


def test_save_protects_existing_and_only_png(tmp_path):
    path=tmp_path/'a.png'; io.save_rgb(pixels(),path); before=path.read_bytes()
    with pytest.raises(FileExistsError): io.save_rgb(255-pixels(),path)
    assert path.read_bytes()==before
    io.save_rgb(255-pixels(),path,overwrite=True)
    np.testing.assert_array_equal(io.load_rgb(path),255-pixels())
    with pytest.raises(ValueError,match='Output'): io.save_rgb(pixels(),tmp_path/'a.jpg')


def test_hashes_are_file_snapshot_and_hwc_bytes(tmp_path):
    path=tmp_path/'a.png'; io.save_rgb(pixels(),path)
    a,record=io._read_rgb(path)
    assert record['file_sha256']==hashlib.sha256(path.read_bytes()).hexdigest()
    assert record['pixel_sha256']==hashlib.sha256(a.tobytes(order='C')).hexdigest()
    assert record['dimensions']==[17,13] and record['size_bytes']==path.stat().st_size
