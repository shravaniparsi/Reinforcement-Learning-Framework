"""Episode and recovery outcomes for the clustered-loss extension."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .schema import TraceSchedule
from .trace_runner import TraceRun


def _episodes(stale: Sequence[bool]) -> list[tuple[int, int]]:
    episodes: list[tuple[int, int]] = []
    start = None
    for index, is_stale in enumerate(stale):
        if is_stale and start is None:
            start = index
        elif not is_stale and start is not None:
            episodes.append((start, index - 1))
            start = None
    if start is not None:
        episodes.append((start, len(stale) - 1))
    return episodes


def summarize_clustered_loss(run: TraceRun, schedule: TraceSchedule) -> Mapping[str, Any]:
    observations = run.observations
    if not observations:
        raise ValueError('clustered-loss summary requires request observations')
    stale = [not item.semantically_fresh for item in observations]
    episodes = _episodes(stale)
    dropped_ids = {item.update_event_id for item in schedule.faults if item.drop}
    dropped_events = [event for event in schedule.events if event.event_id in dropped_ids]
    if not dropped_events:
        return {
            'stale_episode_count': len(episodes),
            'max_consecutive_stale_requests': max((end - start + 1 for start, end in episodes), default=0),
            'max_stale_episode_elapsed_ms': max(
                (observations[end].at_ms - observations[start].at_ms for start, end in episodes),
                default=0,
            ),
            'post_fault_stale_request_count': 0,
            'requests_until_observed_terminal_recovery': 0,
            'terminal_recovery_elapsed_ms': 0,
            'terminal_recovery_right_censored': False,
        }
    final_fault_ms = max(event.at_ms for event in dropped_events)
    post = [(index, item) for index, item in enumerate(observations) if item.at_ms >= final_fault_ms]
    stale_post_positions = [position for position, (_, item) in enumerate(post) if not item.semantically_fresh]
    if not stale_post_positions:
        requests_to_recovery = 0
        recovery_elapsed = 0
        censored = False
    else:
        last_stale_position = stale_post_positions[-1]
        if last_stale_position + 1 >= len(post):
            requests_to_recovery = len(post)
            recovery_elapsed = post[-1][1].at_ms - final_fault_ms
            censored = True
        else:
            recovery = post[last_stale_position + 1][1]
            requests_to_recovery = last_stale_position + 2
            recovery_elapsed = recovery.at_ms - final_fault_ms
            censored = False
    return {
        'stale_episode_count': len(episodes),
        'max_consecutive_stale_requests': max((end - start + 1 for start, end in episodes), default=0),
        'max_stale_episode_elapsed_ms': max(
            (observations[end].at_ms - observations[start].at_ms for start, end in episodes),
            default=0,
        ),
        'post_fault_stale_request_count': len(stale_post_positions),
        'requests_until_observed_terminal_recovery': requests_to_recovery,
        'terminal_recovery_elapsed_ms': recovery_elapsed,
        'terminal_recovery_right_censored': censored,
    }


__all__ = ['summarize_clustered_loss']
