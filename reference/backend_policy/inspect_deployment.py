"""Read-only PyPI metadata and wheel inventories; no installations or builds."""
import datetime
import hashlib
import io
import json
import re
import urllib.request
import zipfile
from .build_corpus import ROOT


def get(url):
    with urllib.request.urlopen(url) as response: return response.read()


def is_native(name):
    return name.endswith(('.dll','.so','.pyd','.dylib')) or '.so.' in name


def inspect():
    report=dict(checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        sources=['https://pypi.org/pypi/pyfftw/json','https://pypi.org/pypi/pyfftw/0.15.0/json'],releases={},wheel_inspections={})
    for version in ('latest','0.15.0'):
        url='https://pypi.org/pypi/pyfftw/'+('json' if version=='latest' else version+'/json')
        meta=json.loads(get(url)); info=meta['info']
        wheels=[dict(filename=f['filename'],size=f['size'],sha256=f['digests']['sha256'],url=f['url']) for f in meta['urls'] if f['filename'].endswith('.whl')]
        report['releases'][version]=dict(version=info['version'],requires_python=info['requires_python'],requires_dist=info['requires_dist'],wheels=wheels)
        if version=='latest':
            for platform in ('win_amd64','macosx_13_0_x86_64','macosx_14_0_arm64','manylinux2014_x86_64'):
                selected=next(w for w in wheels if 'cp312-cp312' in w['filename'] and platform in w['filename'])
                raw=get(selected['url']); assert hashlib.sha256(raw).hexdigest()==selected['sha256']
                with zipfile.ZipFile(io.BytesIO(raw)) as z:
                    native=[dict(name=f.filename,size=f.file_size) for f in z.infolist() if is_native(f.filename)]
                    report['wheel_inspections'][platform]=dict(filename=selected['filename'],download_bytes=len(raw),
                        expanded_bytes=sum(f.file_size for f in z.infolist()),native_binaries=native,
                        fftw_version_markers=sorted(set(m.decode(errors='replace') for f in z.infolist() if is_native(f.filename) for m in re.findall(rb'fftw-3\.[0-9]+\.[0-9]+',z.read(f.filename)))))
    (ROOT/'deployment.json').write_text(json.dumps(report,indent=2)+'\n', newline='\n')
    print({k:(v['version'],v['requires_python']) for k,v in report['releases'].items()})
    print(report['wheel_inspections'])


if __name__=='__main__': inspect()
