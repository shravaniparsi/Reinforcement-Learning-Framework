"""Full-information policies and staged offline analysis for the prospective study.

No browser collection is enabled here. CLI inputs must be new eligible sessions;
legacy/engineering archives fail closed. Synthetic tests are never study evidence.
"""
import argparse
import hashlib
import itertools
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from main_study_design import COUNTS, digest, session_schedule, validate_session

APPS = ('catalog', 'articles', 'external')
ACTIONS = ('ssr', 'csr')  # argmin ties choose SSR
CELLS = tuple(itertools.product(APPS, (1, 4), ('cold', 'warm')))
PENALTIES = (0.01, 0.1, 1.0, 10.0, 100.0)
ENDPOINT = 'mount_hydration_ms'
POLICIES = ('always_ssr', 'always_csr', 'best_fixed', 'engineering_rule', 'context_table', 'ridge')

def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def key(cell):
    return '|'.join(map(str, cell))

def features(cell):
    app, cpu, cache = cell
    # Five main effects plus every pairwise product. Intercept added after scaling.
    main = np.asarray([float(app == a) for a in APPS] + [float(cpu == 4), float(cache == 'warm')])
    return np.asarray([*main, *(main[i]*main[j] for i,j in itertools.combinations(range(5),2))])

def cell_means(rows):
    groups = {(cell, action): [] for cell in CELLS for action in ACTIONS}
    for row in rows:
        cell = (row['application'], row['cpu_rate'], row['cache'])
        groups[cell, row['action']].append(row['metrics'][ENDPOINT])
    if any(len(values) != 3 for values in groups.values()):
        raise ValueError('Exactly three observations per cell/action required')
    return {key(cell): {action: float(np.mean(groups[cell,action])) for action in ACTIONS} for cell in CELLS}

def load_stage(paths, stage, count, launch_sha=None):
    if stage not in COUNTS or count != COUNTS[stage]:
        raise ValueError('Unknown stage or incorrect stage count')
    if len(paths) != count or len({Path(p).resolve() for p in paths}) != count:
        raise ValueError('Stage requires distinct complete session directories')
    sessions, provenance, locks = {}, [], set()
    for path in map(Path, paths):
        manifest = json.loads((path/'manifest.json').read_text())
        if manifest.get('eligible_for_main_study') is not True or manifest.get('purpose') != 'main_study':
            raise ValueError('Engineering/legacy data are ineligible')
        if manifest.get('endpoint') != ENDPOINT:
            raise ValueError('Endpoint differs from amendment v2')
        lock = manifest.get('launch_lock_sha256', '')
        if len(lock) != 64 or any(c not in '0123456789abcdef' for c in lock):
            raise ValueError('Missing launch lock identity')
        locks.add(lock)
        rows = [json.loads(line) for line in (path/'measurements.jsonl').read_text().splitlines()]
        sid = manifest['schedule']['session_id']
        if sid in sessions or sid not in {f'{stage}-{i:02d}' for i in range(count)}:
            raise ValueError('Duplicate or wrong-stage session identity')
        schedule = session_schedule(stage, int(sid.rsplit('-',1)[1]))
        if manifest['schedule'] != schedule:
            raise ValueError('Schedule differs from predeclared design')
        validate_session(rows, schedule)
        sessions[sid] = cell_means(rows)
        provenance.append({'session_id':sid, 'path':str(path.resolve()),
                           'manifest_sha256':file_sha(path/'manifest.json'),
                           'measurements_sha256':file_sha(path/'measurements.jsonl')})
    if len(locks) != 1 or (launch_sha is not None and locks != {launch_sha}):
        raise ValueError('Build/measurement lock differs across stages')
    return {'stage':stage,'sessions':sessions,'provenance':provenance,'launch_lock_sha256':locks.pop()}

def fit_training(data):
    if data['stage'] != 'training': raise ValueError('Fit accepts training data only')
    start = time.perf_counter()
    sessions = data['sessions']
    if len(sessions) != COUNTS['training']: raise ValueError('Incomplete training stage')
    means = {key(c): {a:float(np.mean([s[key(c)][a] for s in sessions.values()])) for a in ACTIONS} for c in CELLS}
    fixed = {app:min(ACTIONS,key=lambda a: np.mean([means[key(c)][a] for c in CELLS if c[0] == app])) for app in APPS}
    table = {k:min(ACTIONS,key=values.get) for k,values in means.items()}
    x = np.asarray([features(c) for s in sessions for c in CELLS])
    center, scale = x.mean(axis=0), x.std(axis=0)
    scale[scale == 0] = 1.0
    z = np.column_stack([np.ones(len(x)),(x-center)/scale])
    penalty_matrix = np.eye(z.shape[1]); penalty_matrix[0,0] = 0
    candidates = {}
    for alpha in PENALTIES:
        candidates[str(alpha)] = {}
        for action in ACTIONS:
            y = np.asarray([s[key(c)][action] for s in sessions.values() for c in CELLS])
            candidates[str(alpha)][action] = np.linalg.solve(z.T@z + alpha*penalty_matrix,z.T@y).tolist()
    return {'artifact_type':'training_fit','endpoint':ENDPOINT,'launch_lock_sha256':data['launch_lock_sha256'],
            'implementation_sha256':file_sha(__file__),'numpy_version':np.__version__,
            'training_provenance':data['provenance'],'best_fixed':fixed,'context_table':table,
            'feature_center':center.tolist(),'feature_scale':scale.tolist(),'ridge_candidates':candidates,
            'training_seconds':time.perf_counter()-start,'training_sessions':len(sessions),
            'feedback':'complete two-action outcomes; equal training table for fitted policies'}

def choose(model, policy, cell, alpha=None):
    if cell not in CELLS: raise ValueError('Unknown predecision context')
    if policy == 'always_ssr': return 'ssr'
    if policy == 'always_csr': return 'csr'
    if policy == 'best_fixed': return model['best_fixed'][cell[0]]
    if policy == 'engineering_rule': return 'csr' if cell == ('external',4,'cold') else 'ssr'
    if policy == 'context_table': return model['context_table'][key(cell)]
    if policy != 'ridge': raise ValueError('Unknown policy')
    z = np.r_[1.0,(features(cell)-model['feature_center'])/model['feature_scale']]
    coefs = model['ridge_candidates'][str(alpha)] if alpha is not None else model['ridge_coefficients']
    scores = {a:float(z@coefs[a]) for a in ACTIONS}
    # Numerically indistinguishable scores follow the declared SSR tie rule.
    return 'ssr' if scores['ssr'] <= scores['csr'] + 1e-10 else 'csr'

def score(model, session, policy, alpha=None):
    return float(np.mean([session[key(c)][choose(model,policy,c,alpha)] for c in CELLS]))

def freeze_validation(model, data):
    if data['stage'] != 'validation' or model['artifact_type'] != 'training_fit':
        raise ValueError('Freeze needs a training fit and validation-only observations')
    if model.get('implementation_sha256') != file_sha(__file__): raise ValueError('Policy implementation changed since training')
    if model['launch_lock_sha256'] != data['launch_lock_sha256']: raise ValueError('Launch lock changed')
    if len(data['sessions']) != COUNTS['validation']: raise ValueError('Incomplete validation stage')
    scores = {str(a):float(np.mean([score(model,s,'ridge',a) for s in data['sessions'].values()])) for a in PENALTIES}
    # Iterating descending and stable min implements larger-penalty exact ties.
    selected = min(reversed(PENALTIES),key=lambda a:scores[str(a)])
    frozen = {k:v for k,v in model.items() if k != 'ridge_candidates'}
    frozen.update(artifact_type='frozen_policies',selected_penalty=selected,
                  ridge_coefficients=model['ridge_candidates'][str(selected)],validation_scores_ms=scores,
                  validation_provenance=data['provenance'],refit_on_validation=False)
    return frozen

def plan_variance(model, data):
    if model['artifact_type'] != 'frozen_policies' or data['stage'] != 'variance':
        raise ValueError('Replication planning requires frozen policies and variance-only data')
    if model.get('implementation_sha256') != file_sha(__file__): raise ValueError('Policy implementation changed since training')
    if model['launch_lock_sha256'] != data['launch_lock_sha256']: raise ValueError('Launch lock changed')
    if len(data['sessions']) != COUNTS['variance']: raise ValueError('Six variance sessions required')
    contrasts = {sid:score(model,s,'context_table')-score(model,s,'best_fixed') for sid,s in data['sessions'].items()}
    sd = float(np.std(list(contrasts.values()),ddof=1))
    uncapped = max(12,math.ceil((1.96*sd/5)**2))
    n = min(48,uncapped)
    return {'artifact_type':'test_replication_plan','endpoint':ENDPOINT,'launch_lock_sha256':data['launch_lock_sha256'],
            'frozen_policy_content_sha256':digest(model),'variance_provenance':data['provenance'],
            'session_contrasts_ms':contrasts,'sample_sd_ms':sd,'target_half_width_ms':5,
            'uncapped_sessions':uncapped,'test_sessions':n,'cap_prevented_target':uncapped>48,
            'test_collection_enabled':False,'test_days_minimum':3,
            'note':'Planning approximation, not achieved precision or statistical power'}

def paired_interval(contrasts, resamples=10000, seed=20260918):
    x=np.asarray(contrasts,dtype=float)
    if len(x)<2 or not np.isfinite(x).all(): raise ValueError('Finite session contrasts required')
    rng=np.random.default_rng(seed)
    draws=x[rng.integers(0,len(x),size=(resamples,len(x)))].mean(axis=1)
    return {'mean_ms':float(x.mean()),'percentile_95_ms':np.quantile(draws,[.025,.975]).tolist(),
            'unit':'whole session','resamples':resamples,'seed':seed}

def save_new(path, payload):
    envelope={'created_utc':datetime.now(timezone.utc).isoformat(),'content_sha256':digest(payload),'payload':payload}
    with Path(path).open('x') as stream: json.dump(envelope,stream,indent=2,allow_nan=False);stream.write('\n')

def read_artifact(path, expected_type):
    envelope=json.loads(Path(path).read_text());payload=envelope['payload']
    if digest(payload)!=envelope['content_sha256'] or payload.get('artifact_type')!=expected_type:
        raise ValueError('Artifact identity/type mismatch')
    return payload

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('operation',choices=['fit','freeze','plan-test'])
    parser.add_argument('--sessions',type=Path,nargs='+',required=True)
    parser.add_argument('--input',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    stage={'fit':'training','freeze':'validation','plan-test':'variance'}[args.operation]
    data=load_stage(args.sessions,stage,COUNTS[stage])
    if args.operation=='fit': result=fit_training(data)
    else:
        if args.input is None: parser.error('--input is required for freeze/plan-test')
        model=read_artifact(args.input,'training_fit' if args.operation=='freeze' else 'frozen_policies')
        result=freeze_validation(model,data) if args.operation=='freeze' else plan_variance(model,data)
    save_new(args.output,result)
    print(f'Wrote {result["artifact_type"]}: {args.output}. No collection authorization granted.')

if __name__=='__main__': main()
