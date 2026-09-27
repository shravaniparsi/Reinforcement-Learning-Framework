"""Synthetic tests only; exercise cohort failure gates and a known policy contrast."""
import copy
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments/cloud_replication_v1'))
from design import schedule, COUNT, PURPOSE, CELLS, POLICIES, HERE
from analyze import validate_cohort, summarize, CHROME


class CloudTransportTests(unittest.TestCase):
    def setUp(self):
        self.entries = []
        for index in range(COUNT):
            plan = schedule(index)
            manifest = dict(allocation_index=index, purpose=PURPOSE, validation='passed',
                            eligible_for_cloud_transport=True, eligible_for_main_study=False,
                            lock_sha256='test-lock', run_attempt='1', run_id='test-run', git_sha='a'*40,
                            schedule=plan, browser_version=CHROME, browser_executable_sha256='b'*64,
                            adapter_injected_by_collector=False, observations=72,
                            adapter_install_checks=[True]*26, started_utc='2026-09-27T01:00:00+00:00')
            receipt = dict(validation='passed', git_sha='a'*40,
                           runner=dict(GITHUB_RUN_ID='test-run', GITHUB_RUN_ATTEMPT='1', RUNNER_ENVIRONMENT='github-hosted'))
            rows = [{**t, 'status': 'ok', 'correctness': True, 'content_sha256': t['pair_id'],
                     'errors': [], 'external_requests': [],
                     'metrics': {'mount_hydration_ms': 10 if t['action']=='ssr' else 22}} for t in plan['trials']]
            self.entries.append((manifest, receipt, rows))

    def test_complete_cohort_and_known_contrast(self):
        validate_cohort(self.entries, 'test-lock')
        actions = {p: {c: 'ssr' for c in CELLS} for p in POLICIES}
        actions['context_table'][CELLS[0]] = 'csr'
        result = summarize(self.entries, actions)
        self.assertEqual(result['contrast_ms']['mean'], 1)
        self.assertEqual(result['relative_reduction_percent'], -10)
        self.assertEqual(result['sign_counts']['positive'], 12)
        self.assertEqual(len(result['cell_results']), 12)

    def test_no_missing_duplicate_or_mixed_allocations(self):
        variants = [self.entries[:-1], self.entries[:-1]+[self.entries[0]]]
        for field, value in [('run_id','other'), ('git_sha','c'*40), ('run_attempt','2'),
                             ('lock_sha256','different'), ('purpose','github_linux_engineering_only'),
                             ('validation','failed'), ('browser_version','other'),
                             ('eligible_for_main_study',True), ('adapter_install_checks',[True]*25)]:
            entries = copy.deepcopy(self.entries); entries[0][0][field] = value; variants.append(entries)
        for entries in variants:
            with self.subTest(variant=variants.index(entries)), self.assertRaises(ValueError):
                validate_cohort(entries, 'test-lock')

    def test_invalid_observations_are_not_dropped(self):
        for field, value in [('correctness',False), ('errors',['failed']), ('external_requests',['https://example.org']),
                             ('metrics',{'mount_hydration_ms':float('nan')}), ('content_sha256','wrong')]:
            entries = copy.deepcopy(self.entries); entries[0][2][0][field]=value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_cohort(entries, 'test-lock')

    def test_schedule_is_frozen_balanced_and_new(self):
        self.assertEqual(schedule(0), schedule(0))
        self.assertEqual(len({schedule(i)['seed'] for i in range(COUNT)}), COUNT)
        for index in (-1, 12, True):
            with self.assertRaises(ValueError): schedule(index)
        for _, _, rows in self.entries:
            self.assertEqual(len({r['pair_id'] for r in rows}), 36)
        actions=json.loads((HERE/'frozen-actions.json').read_text())['actions']
        self.assertEqual(set(actions),set(POLICIES))
        self.assertTrue(all(set(a)==set(CELLS) for a in actions.values()))


if __name__ == '__main__': unittest.main()
