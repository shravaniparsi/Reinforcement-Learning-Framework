"""Export all frozen decisions locally before collection; never refit a policy."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main_study_policies as original

EXPECTED = '8b7ac71519fb3f7db4d1a6be2df337410c24d5e1c8d1cff5d8e96a82ee7ad9e2'
if __name__ == '__main__':
    source, destination = map(Path, sys.argv[1:])
    model = original.read_artifact(source, 'frozen_policies')
    if original.digest(model) != EXPECTED or model['implementation_sha256'] != original.file_sha(original.__file__):
        raise ValueError('Original model or policy implementation differs')
    payload = {'purpose': 'Finite-domain export of original frozen policies; no refitting',
               'original_policy_content_sha256': EXPECTED,
               'original_implementation_sha256': original.file_sha(original.__file__),
               'actions': {p: {original.key(c): original.choose(model, p, c) for c in original.CELLS}
                           for p in original.POLICIES}}
    with destination.open('x') as stream:
        json.dump(payload, stream, indent=2); stream.write('\n')
