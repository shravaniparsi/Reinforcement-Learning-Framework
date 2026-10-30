"""Policy-independent cache gateway for prospective freshness experiments."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Optional

from .workload import WorkloadAdapter, content_hash


POLICIES = frozenset({
    'bypass',
    'conditional-validation',
    'fixed-ttl',
    'stale-while-revalidate',
    'always-invalidate',
    'always-update',
    'write-reactive',
    'event-invalidate-with-repair',
})

EVENT_POLICIES = frozenset({
    'always-invalidate',
    'always-update',
    'write-reactive',
    'event-invalidate-with-repair',
})


@dataclass(frozen=True)
class CacheEntry:
    key: str
    content: Any
    content_sha256: str
    served_revision: int
    validator: Optional[str]
    stored_at_ms: int


@dataclass(frozen=True)
class GatewayObservation:
    policy: str
    key: str
    at_ms: int
    decision_revision: int
    served_revision: int
    content: Any
    content_sha256: str
    oracle_sha256: str
    semantically_fresh: bool
    revision_lag: int
    origin_operation: str
    origin_response_body_bytes: int
    cache_hit: bool


@dataclass
class WriteHistory:
    """Exact per-key counters used by the write-reactive policy."""

    write_sum: int = 0
    sample_count: int = 0
    writes_since_read: int = 0


UpdateMaterializer = Callable[
    [str, CacheEntry, str, Mapping[str, Any], int], Optional[CacheEntry]
]


class CacheGateway:
    """Execute a declared cache policy without owning the workload oracle."""

    def __init__(
        self,
        workload: WorkloadAdapter,
        policy: str,
        *,
        ttl_ms: Optional[int] = None,
        stale_window_ms: Optional[int] = None,
        repair_ms: Optional[int] = None,
        affects: Optional[Callable[[str, str, Mapping[str, Any]], bool]] = None,
        materialize_update: Optional[UpdateMaterializer] = None,
        update_cost: Optional[float] = None,
        invalidate_cost: Optional[float] = None,
        miss_cost: Optional[float] = None,
        initial_expected_writes: Optional[float] = None,
    ) -> None:
        if policy not in POLICIES:
            raise ValueError(f'unsupported gateway policy: {policy}')
        if policy == 'fixed-ttl' and not self._positive_int(ttl_ms):
            raise ValueError('fixed-ttl requires a positive ttl_ms')
        if policy == 'stale-while-revalidate':
            if not self._positive_int(ttl_ms) or not self._positive_int(stale_window_ms):
                raise ValueError('stale-while-revalidate requires positive ttl_ms and stale_window_ms')
        if policy == 'event-invalidate-with-repair' and not self._positive_int(repair_ms):
            raise ValueError('event repair requires a positive repair_ms')
        if policy == 'write-reactive':
            costs = (update_cost, invalidate_cost, miss_cost)
            if any(not self._positive_number(value) for value in costs):
                raise ValueError('write-reactive requires positive update, invalidate and miss costs')
            if not self._positive_number(initial_expected_writes):
                raise ValueError('write-reactive requires positive initial_expected_writes')
        self.workload = workload
        self.policy = policy
        self.ttl_ms = ttl_ms
        self.stale_window_ms = stale_window_ms
        self.repair_ms = repair_ms
        self.affects = affects or (lambda cache_key, notification_key, payload: cache_key == notification_key)
        self.materialize_update = materialize_update or self._materialize_direct_object_update
        self.update_cost = update_cost
        self.invalidate_cost = invalidate_cost
        self.miss_cost = miss_cost
        self.initial_expected_writes = initial_expected_writes
        self.cache: Dict[str, CacheEntry] = {}
        self.notifications: Dict[str, str] = {}
        self.publications: Dict[str, tuple[str, Mapping[str, Any]]] = {}
        self.tracked_keys: set[str] = set()
        self.write_history: Dict[str, WriteHistory] = {}
        self.last_write_action: Dict[str, str] = {}
        self.seed: Optional[int] = None

    @staticmethod
    def _positive_int(value: Optional[int]) -> bool:
        return isinstance(value, int) and not isinstance(value, bool) and value > 0

    @staticmethod
    def _positive_number(value: Optional[float]) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0

    def reset(self, seed: int) -> None:
        self.workload.reset(seed)
        self.cache.clear()
        self.notifications.clear()
        self.publications.clear()
        self.tracked_keys.clear()
        self.write_history.clear()
        self.last_write_action.clear()
        self.seed = seed

    def state(self) -> Mapping[str, Any]:
        return {
            'policy': self.policy,
            'seed': self.seed,
            'cache_keys': tuple(sorted(self.cache)),
            'notification_ids': tuple(sorted(self.notifications)),
            'publication_ids': tuple(sorted(self.publications)),
            'tracked_keys': tuple(sorted(self.tracked_keys)),
            'write_history': {
                key: {
                    'write_sum': history.write_sum,
                    'sample_count': history.sample_count,
                    'writes_since_read': history.writes_since_read,
                }
                for key, history in sorted(self.write_history.items())
            },
            'last_write_action': dict(sorted(self.last_write_action.items())),
        }

    def prepare_notification(
        self,
        publication_id: str,
        key: str,
        payload: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Fix source-side policy actions when an origin write is published."""

        if not isinstance(publication_id, str) or not publication_id:
            raise ValueError('publication_id must be non-empty')
        if not isinstance(key, str) or not key or not isinstance(payload, Mapping):
            raise ValueError('publication key and payload are required')
        source_digest = content_hash({'key': key, 'payload': payload})
        previous = self.publications.get(publication_id)
        if previous is not None:
            if previous[0] != source_digest:
                raise ValueError('publication ID was reused with different content')
            return copy.deepcopy(previous[1])

        prepared = copy.deepcopy(dict(payload))
        actions: Dict[str, str] = {}
        affected_tracked = [
            cache_key for cache_key in self.tracked_keys
            if self.affects(cache_key, key, payload)
        ]
        if self.policy == 'always-update':
            actions = {
                cache_key: 'update'
                for cache_key in affected_tracked
                if cache_key in self.cache
            }
        elif self.policy == 'write-reactive':
            for cache_key in affected_tracked:
                history = self.write_history.setdefault(cache_key, WriteHistory())
                history.writes_since_read += 1
                if cache_key not in self.cache:
                    continue
                expected_writes = (
                    history.write_sum / history.sample_count
                    if history.sample_count else self.initial_expected_writes
                )
                update_total = expected_writes * self.update_cost
                invalidate_total = self.invalidate_cost + self.miss_cost
                action = 'update' if update_total < invalidate_total else 'invalidate'
                actions[cache_key] = action
                self.last_write_action[cache_key] = action
        if actions or self.policy in {'always-update', 'write-reactive'}:
            prepared['_cache_actions'] = actions
        if self.policy in {'always-invalidate', 'event-invalidate-with-repair'}:
            prepared = self._invalidation_metadata(prepared)
        elif self.policy == 'write-reactive' and not any(
            action == 'update' for action in actions.values()
        ):
            prepared = self._invalidation_metadata(prepared)
            prepared['_cache_actions'] = actions
        self.publications[publication_id] = (source_digest, copy.deepcopy(prepared))
        return prepared

    @staticmethod
    def _invalidation_metadata(payload: Mapping[str, Any]) -> Dict[str, Any]:
        excluded = {'content', 'content_sha256', 'record', 'query_updates'}
        return {
            key: copy.deepcopy(value)
            for key, value in payload.items()
            if key not in excluded
        }

    def notify(
        self,
        notification_id: str,
        key: str,
        payload: Mapping[str, Any],
        *,
        at_ms: Optional[int] = None,
    ) -> bool:
        if not isinstance(notification_id, str) or not notification_id:
            raise ValueError('notification_id must be non-empty')
        if not isinstance(key, str) or not key or not isinstance(payload, Mapping):
            raise ValueError('notification key and payload are required')
        if at_ms is not None and (
            not isinstance(at_ms, int) or isinstance(at_ms, bool) or at_ms < 0
        ):
            raise ValueError('at_ms must be a non-negative integer')
        digest = content_hash({'key': key, 'payload': payload})
        previous = self.notifications.get(notification_id)
        if previous is not None:
            if previous != digest:
                raise ValueError('notification ID was reused with different content')
            return False
        declared_actions = payload.get('_cache_actions')
        if declared_actions is not None and not isinstance(declared_actions, Mapping):
            raise ValueError('_cache_actions must be a mapping')
        if declared_actions is None:
            affected = [
                cache_key for cache_key in self.tracked_keys
                if self.affects(cache_key, key, payload)
            ]
        else:
            affected = list(declared_actions)
            if any(
                not isinstance(cache_key, str)
                or declared_actions[cache_key] not in {'update', 'invalidate'}
                for cache_key in affected
            ):
                raise ValueError('_cache_actions contains an invalid action')
        if self.policy in {'always-update', 'write-reactive'} and at_ms is None and affected:
            raise ValueError(f'{self.policy} notifications require at_ms')
        cache_before = copy.deepcopy(self.cache)
        history_before = copy.deepcopy(self.write_history)
        actions_before = dict(self.last_write_action)
        try:
            for cache_key in affected:
                if self.policy in {'always-invalidate', 'event-invalidate-with-repair'}:
                    self.cache.pop(cache_key, None)
                elif self.policy == 'always-update':
                    if declared_actions is not None and declared_actions[cache_key] != 'update':
                        raise ValueError('always-update publication declared a non-update action')
                    self._apply_update(cache_key, key, payload, at_ms)
                    self.last_write_action[cache_key] = 'update'
                elif self.policy == 'write-reactive':
                    if declared_actions is not None:
                        action = declared_actions[cache_key]
                    else:
                        history = self.write_history.setdefault(cache_key, WriteHistory())
                        history.writes_since_read += 1
                        expected_writes = (
                            history.write_sum / history.sample_count
                            if history.sample_count else self.initial_expected_writes
                        )
                        update_total = expected_writes * self.update_cost
                        invalidate_total = self.invalidate_cost + self.miss_cost
                        action = 'update' if update_total < invalidate_total else 'invalidate'
                    if action == 'update':
                        self._apply_update(cache_key, key, payload, at_ms)
                        self.last_write_action[cache_key] = 'update'
                    else:
                        self.cache.pop(cache_key, None)
                        self.last_write_action[cache_key] = 'invalidate'
        except Exception:
            self.cache = cache_before
            self.write_history = history_before
            self.last_write_action = actions_before
            raise
        self.notifications[notification_id] = digest
        return True

    @staticmethod
    def _materialize_direct_object_update(
        cache_key: str,
        entry: CacheEntry,
        notification_key: str,
        payload: Mapping[str, Any],
        at_ms: int,
    ) -> Optional[CacheEntry]:
        query_updates = payload.get('query_updates', {})
        if not isinstance(query_updates, Mapping):
            raise ValueError('query_updates must be a mapping')
        query_update = query_updates.get(cache_key)
        if query_update is not None:
            if not isinstance(query_update, Mapping):
                raise ValueError('query update must be a mapping')
            content = query_update.get('content')
            revision = query_update.get('revision')
            declared_hash = query_update.get('content_sha256')
        else:
            content = payload.get('content')
            revision = payload.get('revision')
            declared_hash = payload.get('content_sha256')
            if cache_key != notification_key or content is None:
                return None
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
            raise ValueError('update notification requires a non-negative revision')
        digest = content_hash(content)
        if declared_hash is not None and declared_hash != digest:
            raise ValueError('update notification content hash does not match content')
        return CacheEntry(
            key=cache_key,
            content=copy.deepcopy(content),
            content_sha256=digest,
            served_revision=revision,
            validator=None,
            stored_at_ms=at_ms,
        )

    def _apply_update(
        self,
        cache_key: str,
        notification_key: str,
        payload: Mapping[str, Any],
        at_ms: int,
    ) -> None:
        entry = self.cache.get(cache_key)
        if entry is None:
            return
        replacement = self.materialize_update(
            cache_key, entry, notification_key, payload, at_ms,
        )
        if replacement is None:
            raise ValueError(
                f'notification lacks sufficient state to update cached key {cache_key}'
            )
        if replacement.key != cache_key:
            raise ValueError('update materializer changed the cache key')
        if replacement.content_sha256 != content_hash(replacement.content):
            raise ValueError('update materializer returned an invalid content hash')
        if replacement.served_revision <= entry.served_revision:
            return
        self.cache[cache_key] = replacement

    def _full_fetch(self, key: str, at_ms: int, decision_revision: int) -> tuple[CacheEntry, int]:
        record = self.workload.read(key)
        if record.decision_revision != decision_revision:
            raise ValueError(
                f'origin revision {record.decision_revision} differs from trace revision '
                f'{decision_revision} for {key}'
            )
        entry = CacheEntry(
            key=key,
            content=copy.deepcopy(record.content),
            content_sha256=record.content_sha256,
            served_revision=record.served_revision,
            validator=record.validator,
            stored_at_ms=at_ms,
        )
        return entry, record.response_body_bytes

    def _validate(
        self, key: str, entry: CacheEntry, at_ms: int, decision_revision: int,
    ) -> tuple[CacheEntry, int]:
        record = self.workload.read(key, validator=entry.validator)
        if record.decision_revision != decision_revision:
            raise ValueError(
                f'origin revision {record.decision_revision} differs from trace revision '
                f'{decision_revision} for {key}'
            )
        if record.not_modified:
            return CacheEntry(
                key=entry.key,
                content=copy.deepcopy(entry.content),
                content_sha256=entry.content_sha256,
                served_revision=entry.served_revision,
                validator=entry.validator,
                stored_at_ms=at_ms,
            ), record.response_body_bytes
        return CacheEntry(
            key=key,
            content=copy.deepcopy(record.content),
            content_sha256=record.content_sha256,
            served_revision=record.served_revision,
            validator=record.validator,
            stored_at_ms=at_ms,
        ), record.response_body_bytes

    def read(self, key: str, at_ms: int, decision_revision: int) -> GatewayObservation:
        if not isinstance(at_ms, int) or isinstance(at_ms, bool) or at_ms < 0:
            raise ValueError('at_ms must be a non-negative integer')
        oracle = self.workload.oracle(key, decision_revision)
        self.tracked_keys.add(key)
        entry = self.cache.get(key)
        origin_operation = 'none'
        response_bytes = 0
        cache_hit = False

        if self.policy == 'bypass':
            served, response_bytes = self._full_fetch(key, at_ms, decision_revision)
            origin_operation = 'fetch'
        elif self.policy == 'conditional-validation':
            if entry is None:
                served, response_bytes = self._full_fetch(key, at_ms, decision_revision)
                origin_operation = 'fetch'
            else:
                served, response_bytes = self._validate(key, entry, at_ms, decision_revision)
                origin_operation = 'validate'
                cache_hit = served.content_sha256 == entry.content_sha256
            self.cache[key] = served
        elif self.policy == 'fixed-ttl':
            if entry is not None and at_ms - entry.stored_at_ms < self.ttl_ms:
                served = entry
                cache_hit = True
            else:
                served, response_bytes = self._full_fetch(key, at_ms, decision_revision)
                origin_operation = 'fetch'
                self.cache[key] = served
        elif self.policy == 'stale-while-revalidate':
            age_ms = None if entry is None else at_ms - entry.stored_at_ms
            if entry is None:
                served, response_bytes = self._full_fetch(key, at_ms, decision_revision)
                origin_operation = 'fetch'
                self.cache[key] = served
            elif age_ms < self.ttl_ms:
                served = entry
                cache_hit = True
            elif age_ms < self.ttl_ms + self.stale_window_ms:
                served = entry
                cache_hit = True
                refreshed, response_bytes = self._validate(key, entry, at_ms, decision_revision)
                origin_operation = 'background-validate'
                self.cache[key] = refreshed
            else:
                served, response_bytes = self._validate(key, entry, at_ms, decision_revision)
                origin_operation = 'validate'
                cache_hit = served.content_sha256 == entry.content_sha256
                self.cache[key] = served
        elif self.policy in {'always-invalidate', 'always-update', 'write-reactive'}:
            if entry is not None:
                served = entry
                cache_hit = True
            else:
                served, response_bytes = self._full_fetch(key, at_ms, decision_revision)
                origin_operation = 'fetch'
                self.cache[key] = served
        elif self.policy == 'event-invalidate-with-repair':
            if entry is None:
                served, response_bytes = self._full_fetch(key, at_ms, decision_revision)
                origin_operation = 'fetch'
                self.cache[key] = served
            elif at_ms - entry.stored_at_ms >= self.repair_ms:
                served, response_bytes = self._validate(key, entry, at_ms, decision_revision)
                origin_operation = 'validate'
                cache_hit = served.content_sha256 == entry.content_sha256
                self.cache[key] = served
            else:
                served = entry
                cache_hit = True
        else:  # pragma: no cover
            raise AssertionError(self.policy)

        if self.policy == 'write-reactive':
            history = self.write_history.setdefault(key, WriteHistory())
            if history.writes_since_read:
                history.write_sum += history.writes_since_read
                history.sample_count += 1
                history.writes_since_read = 0

        return GatewayObservation(
            policy=self.policy,
            key=key,
            at_ms=at_ms,
            decision_revision=decision_revision,
            served_revision=served.served_revision,
            content=copy.deepcopy(served.content),
            content_sha256=served.content_sha256,
            oracle_sha256=oracle.content_sha256,
            semantically_fresh=served.content_sha256 == oracle.content_sha256,
            revision_lag=max(0, decision_revision - served.served_revision),
            origin_operation=origin_operation,
            origin_response_body_bytes=response_bytes,
            cache_hit=cache_hit,
        )
