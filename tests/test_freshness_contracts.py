import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments'))

from freshness.fault_schedule import materialize_notifications
from freshness.schema import FaultDirective, TraceEvent, TraceSchedule, dump_schedule, load_schedule
from freshness.workload import content_hash


class FreshnessContractTests(unittest.TestCase):
    def schedule(self):
        return TraceSchedule(
            trace_id='trace-1',
            seed=29,
            transport_mode='redis-pubsub',
            events=(
                TraceEvent('u1', 10, 'update', 'catalog', 'p1', {'revision': 1}),
                TraceEvent('u2', 20, 'update', 'catalog', 'p1', {'revision': 2}),
                TraceEvent('r1', 30, 'request', 'catalog', 'p1'),
                TraceEvent('u3', 40, 'update', 'catalog', 'p1', {'revision': 3}),
            ),
            faults=(
                FaultDirective('u1', delay_ms=25, duplicate_delays_ms=(30,)),
                FaultDirective('u2', delay_ms=0),
                FaultDirective('u3', drop=True),
            ),
        )

    def test_fault_materialization_retains_loss_duplicates_and_reordering(self):
        delivered, dropped = materialize_notifications(self.schedule())
        self.assertEqual([item.source_event_id for item in delivered], ['u2', 'u1', 'u1'])
        self.assertEqual([item.notification_id for item in delivered], ['u2:0', 'u1:0', 'u1:1'])
        self.assertEqual([item.source_event_id for item in dropped], ['u3'])
        self.assertIsNone(dropped[0].deliver_at_ms)

    def test_schedule_round_trip_and_digest_are_stable(self):
        schedule = self.schedule()
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / 'schedule.json')
            dump_schedule(schedule, path)
            loaded = load_schedule(path)
        self.assertEqual(loaded, schedule)
        self.assertEqual(loaded.digest(), schedule.digest())
        self.assertEqual(loaded.trace_digest(), schedule.trace_digest())
        self.assertEqual(loaded.fault_digest(), schedule.fault_digest())

        changed_fault = TraceSchedule(
            trace_id=schedule.trace_id,
            seed=schedule.seed,
            transport_mode=schedule.transport_mode,
            events=schedule.events,
            faults=(FaultDirective('u1', delay_ms=26),),
        )
        self.assertEqual(changed_fault.trace_digest(), schedule.trace_digest())
        self.assertNotEqual(changed_fault.fault_digest(), schedule.fault_digest())

    def test_invalid_fault_reference_and_event_order_fail(self):
        event = TraceEvent('r1', 10, 'request', 'catalog', 'p1')
        with self.assertRaisesRegex(ValueError, 'update events'):
            TraceSchedule('bad', 1, 'redis-streams', (event,), (FaultDirective('r1'),))
        with self.assertRaisesRegex(ValueError, 'ordered'):
            TraceSchedule(
                'bad-order',
                1,
                'redis-streams',
                (
                    TraceEvent('r2', 20, 'request', 'catalog', 'p1'),
                    TraceEvent('r1', 10, 'request', 'catalog', 'p1'),
                ),
            )

    def test_content_hash_preserves_semantic_list_order(self):
        first = {'items': [{'id': 1}, {'id': 2}], 'meta': {'revision': 3}}
        same_mapping_different_key_order = {'meta': {'revision': 3}, 'items': [{'id': 1}, {'id': 2}]}
        reordered = {'items': [{'id': 2}, {'id': 1}], 'meta': {'revision': 3}}
        self.assertEqual(content_hash(first), content_hash(same_mapping_different_key_order))
        self.assertNotEqual(content_hash(first), content_hash(reordered))


if __name__ == '__main__':
    unittest.main()
