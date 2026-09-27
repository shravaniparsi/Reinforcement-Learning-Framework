"""Offline reproduction of frozen-policy scores from the candidate's raw observations."""
import hashlib
import json
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'source/experiments'))
from main_study_design import validate_session


def main():
    inventory = json.loads((ROOT/'inventory.json').read_text())
    for name, expected in inventory['files'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != expected:
            raise ValueError('Changed file: '+name)
    model = json.loads((ROOT/'frozen-actions.json').read_text())['actions']
    expected = json.loads((ROOT/'expected-results.json').read_text())
    result = {}
    for cohort in ('mac','cloud'):
        units = json.loads((ROOT/f'data/{cohort}/units.json').read_text())
        if len(units) != 12 or len({u['session_id'] for u in units}) != 12:
            raise ValueError('Incomplete or duplicate cohort')
        values = {p: [] for p in model}
        for unit in units:
            rows = [json.loads(line) for line in (ROOT/unit['records']).read_text().splitlines()]
            validate_session(rows,unit['schedule'])
            if any(r['errors'] or r['external_requests'] for r in rows):
                raise ValueError('Invalid retained observation')
            for p, action_map in model.items():
                cell_means=[]
                for cell, action in action_map.items():
                    app,cpu,cache=cell.split('|')
                    selected=[r['metrics']['mount_hydration_ms'] for r in rows
                              if (r['application'],r['cpu_rate'],r['cache'],r['action'])==(app,int(cpu),cache,action)]
                    if len(selected)!=3:raise ValueError('Unbalanced cell')
                    cell_means.append(float(np.mean(selected)))
                values[p].append(float(np.mean(cell_means)))
        means={p:float(np.mean(v)) for p,v in values.items()}
        diff=np.asarray(values['context_table'])-np.asarray(values['best_fixed'])
        result[cohort]={'policy_means_ms':means,'context_minus_fixed_ms':float(diff.mean()),
                        'negative':int(sum(diff<0)),'positive':int(sum(diff>0))}
        for p,mean in means.items():
            if not np.isclose(mean,expected[cohort]['policy_means_ms'][p],rtol=0,atol=1e-9):
                raise ValueError('Policy mean differs')
        if not np.isclose(diff.mean(),expected[cohort]['contrast_ms'],rtol=0,atol=1e-9):
            raise ValueError('Contrast differs')
        if cohort=='mac':
            rng=np.random.default_rng(20260918)
            interval=np.quantile(diff[rng.integers(0,12,size=(10000,12))].mean(axis=1),[.025,.975])
            if not np.allclose(interval,expected['mac']['conditional_interval_ms'],rtol=0,atol=1e-9):
                raise ValueError('Original conditional interval differs')
            result[cohort]['conditional_interval_ms']=interval.tolist()
    print(json.dumps(result,indent=2))
    print('PASS: checksums, 1,728 observations, complete schedules, both cohorts, six policies each and original Mac conditional interval. No collection or refitting.')


if __name__=='__main__':main()
