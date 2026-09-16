"""Bounded tracked-tree provenance inventory; scan findings never echo secrets."""
from collections import Counter, defaultdict
import hashlib
from importlib import metadata
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
PATH_PATTERN=re.compile(r'(?:[A-Za-z]:[\\/]+(?:Users|Program Files)|/home/|/Users/)',re.I)
SECRET_PATTERNS={
    'private_key':re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'github_token':re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})'),
    'aws_access_key':re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'assigned_secret':re.compile(r'''(?i)(?:api_key|access_token|password|client_secret)\s*[:=]\s*["'][^"'\s]{12,}["']'''),
}


def classify(path):
    if path.startswith('shine_color/'): return 'original_python_implementation'
    if path in ('docs/OCTAVE_HSV_SPEC.md','docs/OCTAVE_LAB_SPEC.md'): return 'behavioral_specification'
    if path.startswith('docs/') or path.endswith('README.md'): return 'documentation'
    if path.startswith('tests/') and '/fixtures/' not in path: return 'tests'
    if '/fixtures/' in path or '/data/' in path: return 'generated_reference_fixture'
    if path.startswith('reference/') and path.endswith(('.py','.m')): return 'original_reference_or_diagnostic_harness'
    if path.startswith('reference/') and path.endswith(('.mat','.json','.csv')): return 'diagnostic_evidence'
    return 'project_configuration'


def text_leaves(value):
    """Find MAT string metadata, without iterating numeric image elements."""
    import numpy as np
    if isinstance(value,str): yield value
    elif hasattr(value,'_fieldnames'):
        for name in value._fieldnames: yield from text_leaves(getattr(value,name))
    elif isinstance(value,np.ndarray):
        if value.dtype.kind in 'US': yield ' '.join(str(x) for x in value.ravel())
        elif value.dtype.kind=='O':
            for item in value.ravel(): yield from text_leaves(item)


def audit(reference, destination):
    from scipy.io import loadmat, whosmat
    reference=Path(reference); destination=Path(destination)
    destination.mkdir(parents=True,exist_ok=True)
    paths=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')[:-1]
    records=[]; overlaps=[]
    upstream=defaultdict(list); upstream_hashes={}
    for p in reference.rglob('*.m'):
        data=p.read_bytes(); upstream_hashes[hashlib.sha256(data).hexdigest()]=p.relative_to(reference).as_posix()
        for line in data.decode('utf-8',errors='replace').splitlines():
            line=line.strip().lstrip('%#').strip()
            if len(line)>=40: upstream[line].append(p.relative_to(reference).as_posix())
    for name in paths:
        p=ROOT/name; data=p.read_bytes()
        record=dict(path=name,category=classify(name),bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
        if p.suffix=='.mat':
            record['mat_variables']=[dict(name=n,shape=list(s),type=t) for n,s,t in whosmat(p)]
            loaded=loadmat(p,struct_as_record=False,squeeze_me=True)
            strings='\n'.join(s for value in loaded.values() for s in text_leaves(value))
        elif p.suffix=='.png': strings=''
        else: strings=data.decode('utf-8',errors='replace')
        record['absolute_path_lines']=[i for i,line in enumerate(strings.splitlines(),1) if PATH_PATTERN.search(line)]
        record['secret_findings']={kind:[i for i,line in enumerate(strings.splitlines(),1) if pattern.search(line)] for kind,pattern in SECRET_PATTERNS.items()}
        record['secret_findings']={k:v for k,v in record['secret_findings'].items() if v}
        record['identical_upstream_source']=upstream_hashes.get(record['sha256'])
        if p.suffix in ('.py','.m'):
            for i,line in enumerate(strings.splitlines(),1):
                key=line.strip().lstrip('%#').strip()
                if key in upstream: overlaps.append(dict(path=name,line=i,upstream=upstream[key]))
        records.append(record)
    packages=[]
    for name,role in [('numpy','runtime'),('Pillow','runtime'),('pytest','dev'),('scipy','dev/reference'),
                      ('scikit-image','optional reference'),('pyFFTW','optional FFT diagnostic'),
                      ('matplotlib','local figure tool; not a project requirement')]:
        try:
            dist=metadata.distribution(name); meta=dist.metadata
            license_files=[]
            for p in dist.files or []:
                if ('dist-info/' in str(p) and any(token in p.name.lower() for token in ('license','copying','notice'))):
                    license_files.append(dict(path=str(p),sha256=hashlib.sha256(dist.locate_file(p).read_bytes()).hexdigest()))
            packages.append(dict(name=name,role=role,version=dist.version,license_expression=meta.get('License-Expression'),
                declared_license=meta.get('License'),license_classifiers=[c for c in meta.get_all('Classifier',[]) if c.startswith('License')],license_files=license_files))
        except metadata.PackageNotFoundError: packages.append(dict(name=name,role=role,installed=False))
    # History scan is supplementary: findings list object IDs/paths, never values.
    history=[]
    entries=[]
    for entry in subprocess.check_output(['git','rev-list','--objects','--all'],cwd=ROOT,text=True).splitlines():
        oid,_,name=entry.partition(' ')
        if name: entries.append((oid,name))
    # A single git process avoids hundreds of Windows process startups.
    payload=subprocess.check_output(['git','cat-file','--batch'],cwd=ROOT,
        input=('\n'.join(oid for oid,_ in entries)+'\n').encode())
    cursor=0
    for oid,name in entries:
        end=payload.index(b'\n',cursor)
        header=payload[cursor:end].decode().split(); size=int(header[2])
        data=payload[end+1:end+1+size]; cursor=end+size+2
        if header[1]!='blob': continue
        text=data.decode('utf-8',errors='replace')
        secrets=[k for k,pattern in SECRET_PATTERNS.items() if pattern.search(text)]
        private=bool(re.search(r'(?:^|/)(?:arch_study|\.cache|\.venv)/|\.(?:pem|key|env)$',name))
        if secrets or private: history.append(dict(object=oid,path=name,secret_patterns=secrets,private_path=private))
    result=dict(schema_version=1,scope='entire tracked working tree plus reachable history secret/private-path scan',
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        counts=dict(Counter(r['category'] for r in records)),files=records,source_line_overlap_candidates=overlaps,
        dependencies=packages,history_findings=history,
        limitation='Pattern scans and line overlap are evidence, not legal clearance or proof of absence of every possible secret or derivation.')
    (destination/'tracked_tree_audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result
