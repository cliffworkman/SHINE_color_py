"""Promote exact archived Octave outputs, verifying the study's recorded hashes."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent


def promote():
    study = ROOT/'backend_policy'
    result = json.loads((study/'results.json').read_text())
    destination = ROOT.parent/'tests/reference/fixtures/conditioned'
    destination.mkdir(exist_ok=True)
    for name, digest in result['reference_output_sha256'].items():
        source = ROOT/'.cache/backend_policy'/name
        assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
        shutil.copyfile(source, destination/name)
    (destination/'provenance.json').write_text(json.dumps(dict(
        study_commit='67ab54f75900b79258726c500b52a0dbe4b566e0',
        source_commit='870e058fe8bf1e4090baf2401ff0e127d1c0237a',
        output_sha256=result['reference_output_sha256']), indent=2)+'\n', newline='\n')


if __name__ == '__main__':
    promote()
