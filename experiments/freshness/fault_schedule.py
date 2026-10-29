"""Materialize notification delivery without hiding dropped messages."""

from __future__ import annotations

from typing import Dict, List, Tuple

from .schema import FaultDirective, ScheduledNotification, TraceSchedule


def materialize_notifications(
    schedule: TraceSchedule,
) -> Tuple[Tuple[ScheduledNotification, ...], Tuple[ScheduledNotification, ...]]:
    """Return delivered and dropped notifications for an exogenous schedule.

    Delivery is ordered by scheduled delivery time. Stable source and copy
    indices make ties deterministic and expose reordering relative to updates.
    """
    faults: Dict[str, FaultDirective] = {
        fault.update_event_id: fault for fault in schedule.faults
    }
    delivered: List[ScheduledNotification] = []
    dropped: List[ScheduledNotification] = []
    source_sequence = 0

    for event in schedule.events:
        if event.kind != 'update':
            continue
        directive = faults.get(event.event_id, FaultDirective(event.event_id))
        if directive.drop:
            dropped.append(
                ScheduledNotification(
                    notification_id=f'{event.event_id}:0',
                    source_event_id=event.event_id,
                    source_sequence=source_sequence,
                    copy_index=0,
                    created_at_ms=event.at_ms,
                    deliver_at_ms=None,
                    dropped=True,
                    workload=event.workload,
                    key=event.key,
                    payload=dict(event.payload),
                )
            )
        else:
            delays = (directive.delay_ms,) + directive.duplicate_delays_ms
            for copy_index, delay_ms in enumerate(delays):
                delivered.append(
                    ScheduledNotification(
                        notification_id=f'{event.event_id}:{copy_index}',
                        source_event_id=event.event_id,
                        source_sequence=source_sequence,
                        copy_index=copy_index,
                        created_at_ms=event.at_ms,
                        deliver_at_ms=event.at_ms + delay_ms,
                        dropped=False,
                        workload=event.workload,
                        key=event.key,
                        payload=dict(event.payload),
                    )
                )
        source_sequence += 1

    delivered.sort(
        key=lambda item: (item.deliver_at_ms, item.source_sequence, item.copy_index)
    )
    return tuple(delivered), tuple(dropped)
