"""Versioned multi-entity origin for the React-admin dashboard workload."""

from __future__ import annotations

import copy
import json
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Mapping, Optional, Tuple
from urllib.parse import parse_qs, urlsplit

from .workload import CommitRecord, OracleSnapshot, ReadRecord, content_hash


RESOURCES = ('orders', 'reviews', 'customers')
ANCHOR_TIME = datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc)
RESOURCE_FIELDS = {
    'orders': frozenset({'id', 'date', 'status', 'total', 'basket', 'customer_id'}),
    'reviews': frozenset({'id', 'date', 'status', 'rating', 'comment', 'customer_id'}),
    'customers': frozenset({'id', 'first_name', 'last_name', 'avatar', 'first_seen', 'has_ordered'}),
}
FILTER_FIELDS = {
    'orders': frozenset({'id', 'date_gte', 'status', 'customer_id'}),
    'reviews': frozenset({'id', 'status', 'customer_id'}),
    'customers': frozenset({'id', 'has_ordered', 'first_seen_gte'}),
}


def _encoded(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False,
    ).encode('utf-8')


def _iso(value: datetime) -> str:
    return value.isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def _json_parameter(args: Mapping[str, List[str]], name: str, default: Any) -> Any:
    values = args.get(name)
    if values is None:
        return default
    if len(values) != 1:
        raise ValueError(f'{name} must appear once')
    try:
        return json.loads(values[0])
    except json.JSONDecodeError as error:
        raise ValueError(f'{name} must be valid JSON') from error


def parse_dashboard_query(key_or_query: str) -> Tuple[str, str, Dict, str, str, int, int]:
    if not isinstance(key_or_query, str):
        raise ValueError('dashboard query must be a string')
    parsed = urlsplit(key_or_query if '://' in key_or_query else f'http://origin{key_or_query}')
    path = parsed.path
    if path.startswith('/api/'):
        resource = path.removeprefix('/api/')
    elif path.startswith('/'):
        resource = path.removeprefix('/')
    else:
        resource = path
    if resource not in RESOURCES:
        raise ValueError(f'unsupported dashboard resource: {resource}')
    args = parse_qs(parsed.query, keep_blank_values=True)
    unknown = set(args) - {'filter', 'sort', 'range'}
    if unknown:
        raise ValueError(f'unknown query parameters: {sorted(unknown)}')
    filters = _json_parameter(args, 'filter', {})
    sort = _json_parameter(args, 'sort', ['id', 'ASC'])
    item_range = _json_parameter(args, 'range', [0, 99])
    if not isinstance(filters, dict) or set(filters) - FILTER_FIELDS[resource]:
        raise ValueError(f'unsupported {resource} filter')
    if (
        not isinstance(sort, list) or len(sort) != 2 or sort[0] not in RESOURCE_FIELDS[resource]
        or sort[1] not in {'ASC', 'DESC'}
    ):
        raise ValueError(f'unsupported {resource} sort')
    if (
        not isinstance(item_range, list) or len(item_range) != 2
        or any(not isinstance(value, int) or isinstance(value, bool) for value in item_range)
        or item_range[0] < 0 or item_range[1] < item_range[0] or item_range[1] - item_range[0] >= 100
    ):
        raise ValueError('range must be an inclusive pair covering at most 100 records')
    canonical = json.dumps(
        {'resource': resource, 'filter': filters, 'sort': sort, 'range': item_range},
        sort_keys=True, separators=(',', ':'), allow_nan=False,
    )
    return canonical, resource, filters, sort[0], sort[1], item_range[0], item_range[1]


class DashboardWorkload:
    """Small deterministic origin with complete snapshots at each commit revision."""

    workload_id = 'react-admin-dashboard-v1'

    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.snapshots: Dict[int, Dict[str, List[Dict[str, Any]]]] = {}
        self.reset(0)

    def close(self) -> None:
        pass

    def reset(self, seed: int) -> None:
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise ValueError('seed must be an integer')
        with self.lock:
            self.snapshots = {0: self._fixtures(seed)}

    @staticmethod
    def _fixtures(seed: int) -> Dict[str, List[Dict[str, Any]]]:
        customers = []
        for index in range(1, 9):
            customers.append({
                'id': index,
                'first_name': f'Customer{index}',
                'last_name': 'Fixture',
                'avatar': (
                    'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" '
                    'width="32" height="32"%3E%3Crect width="32" height="32" '
                    'fill="%23888"/%3E%3C/svg%3E'
                ),
                'first_seen': _iso(ANCHOR_TIME - timedelta(days=index * 4)),
                'has_ordered': index != 8,
            })
        statuses = ('ordered', 'delivered', 'cancelled')
        orders = []
        for index in range(1, 13):
            orders.append({
                'id': index,
                'date': _iso(ANCHOR_TIME - timedelta(days=index)),
                'status': statuses[(index + seed) % len(statuses)],
                'total': 40 + index * 7,
                'basket': [{'product_id': 100 + index, 'quantity': 1 + index % 2}],
                'customer_id': 1 + (index - 1) % len(customers),
            })
        review_statuses = ('pending', 'accepted', 'pending', 'rejected')
        reviews = []
        for index in range(1, 7):
            reviews.append({
                'id': index,
                'date': _iso(ANCHOR_TIME - timedelta(days=index * 2)),
                'status': review_statuses[(index - 1 + seed) % len(review_statuses)],
                'rating': 1 + index % 5,
                'comment': f'Controlled review {index}.',
                'customer_id': 1 + (index - 1) % len(customers),
            })
        return {'orders': orders, 'reviews': reviews, 'customers': customers}

    def _revision(self) -> int:
        return max(self.snapshots)

    def commit(self, mutation: Mapping[str, Any], at_ms: int) -> CommitRecord:
        if not isinstance(at_ms, int) or isinstance(at_ms, bool) or at_ms < 0:
            raise ValueError('at_ms must be a non-negative integer')
        if not isinstance(mutation, Mapping):
            raise ValueError('mutation must be a mapping')
        resource = mutation.get('resource')
        operation = mutation.get('operation')
        if resource not in RESOURCES or operation not in {'create', 'update', 'delete'}:
            raise ValueError('mutation requires a declared resource and create, update or delete')
        with self.lock:
            revision = self._revision() + 1
            state = copy.deepcopy(self.snapshots[revision - 1])
            records = state[resource]
            record_id = mutation.get('id')
            if operation == 'create':
                supplied = mutation.get('record')
                if not isinstance(supplied, Mapping):
                    raise ValueError('create requires a record mapping')
                record = dict(supplied)
                record_id = record.get('id')
                self._validate_record(resource, record)
                if any(item['id'] == record_id for item in records):
                    raise ValueError('record id already exists')
                records.append(record)
            else:
                positions = [index for index, item in enumerate(records) if item['id'] == record_id]
                if len(positions) != 1:
                    raise KeyError(record_id)
                position = positions[0]
                if operation == 'delete':
                    record = records.pop(position)
                else:
                    changes = mutation.get('changes')
                    if not isinstance(changes, Mapping) or not changes or 'id' in changes:
                        raise ValueError('update requires non-empty changes without id')
                    record = {**records[position], **dict(changes)}
                    self._validate_record(resource, record)
                    records[position] = record
            self.snapshots[revision] = state
            return CommitRecord(
                revision=revision,
                committed_at_ms=at_ms,
                affected_keys=(f'{resource}:{record_id}',),
                notification_payload={
                    'resource': resource,
                    'operation': operation,
                    'id': record_id,
                    'revision': revision,
                    'record': copy.deepcopy(record) if operation != 'delete' else None,
                },
            )

    @staticmethod
    def _validate_record(resource: str, record: Mapping[str, Any]) -> None:
        if set(record) != RESOURCE_FIELDS[resource]:
            raise ValueError(f'{resource} record fields must equal {sorted(RESOURCE_FIELDS[resource])}')
        if not isinstance(record['id'], int) or isinstance(record['id'], bool) or record['id'] < 1:
            raise ValueError('record id must be a positive integer')
        if resource == 'orders':
            if record['status'] not in {'ordered', 'delivered', 'cancelled'}:
                raise ValueError('unsupported order status')
            if not isinstance(record['total'], int) or record['total'] < 0:
                raise ValueError('order total must be a non-negative integer')
            if not isinstance(record['basket'], list):
                raise ValueError('order basket must be a list')
        elif resource == 'reviews':
            if record['status'] not in {'pending', 'accepted', 'rejected'}:
                raise ValueError('unsupported review status')
            if not isinstance(record['rating'], int) or not 1 <= record['rating'] <= 5:
                raise ValueError('review rating must be from 1 to 5')
        elif resource == 'customers':
            if not isinstance(record['has_ordered'], bool):
                raise ValueError('customer has_ordered must be boolean')

    @staticmethod
    def _matches(resource: str, record: Mapping[str, Any], filters: Mapping[str, Any]) -> bool:
        for field, wanted in filters.items():
            if field == 'id':
                ids = wanted if isinstance(wanted, list) else [wanted]
                if record['id'] not in ids and str(record['id']) not in ids:
                    return False
            elif field == 'date_gte':
                if record['date'] < wanted:
                    return False
            elif field == 'first_seen_gte':
                if record['first_seen'] < wanted:
                    return False
            elif record.get(field) != wanted:
                return False
        return True

    def _query(self, revision: int, key_or_query: str) -> Tuple[str, List[Dict[str, Any]], int]:
        _, resource, filters, sort_field, sort_order, first, last = parse_dashboard_query(key_or_query)
        try:
            records = self.snapshots[revision][resource]
        except KeyError as error:
            raise KeyError(revision) from error
        matching = [copy.deepcopy(record) for record in records if self._matches(resource, record, filters)]
        matching.sort(key=lambda record: (record[sort_field], record['id']), reverse=sort_order == 'DESC')
        return resource, matching[first:last + 1], len(matching)

    def read(self, key_or_query: str, validator: Optional[str] = None) -> ReadRecord:
        with self.lock:
            revision = self._revision()
            resource, records, total = self._query(revision, key_or_query)
        content = {'resource': resource, 'records': records, 'total': total}
        digest = content_hash(content)
        current_validator = f'"{resource}:{digest}"'
        not_modified = validator == current_validator
        return ReadRecord(
            decision_revision=revision,
            served_revision=revision,
            content=content,
            content_sha256=digest,
            validator=current_validator,
            origin_read=True,
            response_body_bytes=0 if not_modified else len(_encoded(records)),
            not_modified=not_modified,
        )

    def oracle(self, key_or_query: str, decision_revision: int) -> OracleSnapshot:
        if not isinstance(decision_revision, int) or isinstance(decision_revision, bool) or decision_revision < 0:
            raise ValueError('decision_revision must be a non-negative integer')
        with self.lock:
            resource, records, total = self._query(decision_revision, key_or_query)
        content = {'resource': resource, 'records': records, 'total': total}
        return OracleSnapshot(
            decision_revision=decision_revision,
            content=content,
            content_sha256=content_hash(content),
        )

    def dashboard_oracle(self, decision_revision: int) -> OracleSnapshot:
        order_start = _iso(ANCHOR_TIME - timedelta(days=30))
        customer_start = _iso(ANCHOR_TIME - timedelta(days=60))
        with self.lock:
            _, orders, _ = self._query(
                decision_revision,
                '/api/orders?filter=' + json.dumps({'date_gte': order_start})
                + '&sort=' + json.dumps(['date', 'DESC']) + '&range=' + json.dumps([0, 49]),
            )
            _, reviews, review_total = self._query(
                decision_revision,
                '/api/reviews?filter=' + json.dumps({'status': 'pending'})
                + '&sort=' + json.dumps(['date', 'DESC']) + '&range=' + json.dumps([0, 99]),
            )
            _, customers, customer_total = self._query(
                decision_revision,
                '/api/customers?filter=' + json.dumps(
                    {'has_ordered': True, 'first_seen_gte': customer_start}
                ) + '&sort=' + json.dumps(['first_seen', 'DESC']) + '&range=' + json.dumps([0, 99]),
            )
            state_customers = {item['id']: copy.deepcopy(item) for item in self.snapshots[decision_revision]['customers']}
        active_orders = [order for order in orders if order['status'] != 'cancelled']
        pending_orders = [order for order in active_orders if order['status'] == 'ordered']
        content = {
            'orders': orders,
            'revenue': sum(order['total'] for order in active_orders),
            'new_order_count': len(active_orders),
            'pending_orders': pending_orders,
            'pending_reviews': reviews,
            'pending_review_count': review_total,
            'new_customers': customers,
            'new_customer_count': customer_total,
            'referenced_customers': {
                str(customer_id): state_customers[customer_id]
                for customer_id in sorted({
                    *(order['customer_id'] for order in pending_orders),
                    *(review['customer_id'] for review in reviews),
                })
            },
        }
        return OracleSnapshot(
            decision_revision=decision_revision,
            content=content,
            content_sha256=content_hash(content),
        )
