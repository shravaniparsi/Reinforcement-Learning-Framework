"""Conservative query-dependency rules for delivered notifications."""

from __future__ import annotations

from typing import Any, Mapping

from .dashboard_workload import parse_dashboard_query
from .realworld_workload import parse_feed_query


def realworld_feed_affects(
    cache_key: str, notification_key: str, payload: Mapping[str, Any]
) -> bool:
    """Return whether an article mutation can change a cached feed response."""

    del notification_key
    _, tag, _, _ = parse_feed_query(cache_key)
    if tag is None:
        return True
    previous_tags = payload.get('previous_tags', [])
    current_tags = payload.get('current_tags', [])
    if not isinstance(previous_tags, list) or not isinstance(current_tags, list):
        raise ValueError('article notification tags must be lists')
    return tag in previous_tags or tag in current_tags


def dashboard_query_affects(
    cache_key: str, notification_key: str, payload: Mapping[str, Any]
) -> bool:
    """Return whether a resource mutation can change a cached list query."""

    del notification_key
    _, resource, _, _, _, _, _ = parse_dashboard_query(cache_key)
    notification_resource = payload.get('resource')
    if not isinstance(notification_resource, str):
        raise ValueError('dashboard notification requires a resource')
    return resource == notification_resource
