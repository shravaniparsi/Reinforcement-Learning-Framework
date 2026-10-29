"""Mutable RealWorld article-feed workload with historical query snapshots."""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Mapping, Optional, Tuple
from urllib.parse import parse_qs, urlsplit

from .workload import CommitRecord, OracleSnapshot, ReadRecord, content_hash


ALLOWED_TAGS = ('rendering', 'accessibility')
UPDATE_FIELDS = frozenset(
    {'title', 'description', 'body', 'tagList', 'createdAt', 'created_seq', 'favoritesCount'}
)


def _encoded(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
        allow_nan=False,
    ).encode('utf-8')


def _time_string(at_ms: int) -> str:
    value = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(milliseconds=at_ms)
    return value.isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def parse_feed_query(key_or_query: str) -> Tuple[str, Optional[str], int, int]:
    if not isinstance(key_or_query, str):
        raise ValueError('feed query must be a string')
    if key_or_query in {'', '/api/articles'}:
        query = ''
    elif '?' in key_or_query:
        parsed = urlsplit(key_or_query)
        if parsed.path not in {'', '/api/articles'}:
            raise ValueError('only /api/articles feed queries are supported')
        query = parsed.query
    else:
        query = key_or_query
    args = {} if query == '' else parse_qs(query, keep_blank_values=True, strict_parsing=True)
    unknown = set(args) - {'tag', 'limit', 'offset'}
    if unknown or any(len(values) != 1 for values in args.values()):
        raise ValueError('feed query has unknown or repeated parameters')
    tag = args.get('tag', [None])[0]
    if tag == '':
        tag = None
    if tag not in (None,) + ALLOWED_TAGS:
        raise ValueError('unsupported feed tag')
    try:
        limit = int(args.get('limit', ['10'])[0])
        offset = int(args.get('offset', ['0'])[0])
    except ValueError as error:
        raise ValueError('limit and offset must be integers') from error
    if not 1 <= limit <= 20 or not 0 <= offset <= 1000:
        raise ValueError('feed query is outside declared bounds')
    canonical = f'tag={tag or ""}&limit={limit}&offset={offset}'
    return canonical, tag, limit, offset


class RealWorldFeedWorkload:
    workload_id = 'svelte-realworld-feed-v1'

    def __init__(self, article_count: int = 30) -> None:
        if not isinstance(article_count, int) or isinstance(article_count, bool) or article_count < 20:
            raise ValueError('article_count must be an integer of at least 20')
        self.article_count = article_count
        self.lock = threading.RLock()
        self.connection = sqlite3.connect(':memory:', check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.reset(seed=0)

    def close(self) -> None:
        with self.lock:
            self.connection.close()

    def reset(self, seed: int) -> None:
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise ValueError('seed must be an integer')
        with self.lock, self.connection:
            self.connection.executescript(
                '''
                DROP TABLE IF EXISTS metadata;
                DROP TABLE IF EXISTS article_versions;
                CREATE TABLE metadata (
                    key TEXT PRIMARY KEY,
                    value INTEGER NOT NULL
                );
                CREATE TABLE article_versions (
                    slug TEXT NOT NULL,
                    valid_from_revision INTEGER NOT NULL,
                    valid_to_revision INTEGER,
                    created_seq INTEGER NOT NULL,
                    content_json TEXT NOT NULL,
                    PRIMARY KEY (slug, valid_from_revision)
                );
                CREATE INDEX article_snapshot_idx
                    ON article_versions (valid_from_revision, valid_to_revision, created_seq);
                '''
            )
            self.connection.executemany(
                'INSERT INTO metadata (key, value) VALUES (?, ?)',
                [('seed', seed), ('global_revision', 0)],
            )
            for index in range(self.article_count):
                article = self._fixture_article(index, seed)
                self.connection.execute(
                    '''INSERT INTO article_versions
                       (slug, valid_from_revision, valid_to_revision, created_seq, content_json)
                       VALUES (?, 0, NULL, ?, ?)''',
                    (article['slug'], article['created_seq'], _encoded(self._public(article)).decode('utf-8')),
                )

    @staticmethod
    def _fixture_article(index: int, seed: int) -> Dict[str, Any]:
        return {
            'slug': f'independent-note-{index}',
            'title': f'Independent note {index:02d}',
            'description': f'Local reproducibility fixture {index:02d}.',
            'body': 'Synthetic local article.',
            'tagList': [ALLOWED_TAGS[index % 2]],
            'createdAt': '2026-01-01T00:00:00.000Z',
            'updatedAt': '2026-01-01T00:00:00.000Z',
            'favorited': False,
            'favoritesCount': (index + seed) % 3,
            'author': {
                'username': 'fixture-author',
                'bio': 'Local fixture',
                'image': 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="32" height="32"%3E%3Crect width="32" height="32" fill="%23888"/%3E%3C/svg%3E',
                'following': False,
            },
            'created_seq': index,
        }

    @staticmethod
    def _public(article: Mapping[str, Any]) -> Dict[str, Any]:
        return {key: value for key, value in article.items() if key != 'created_seq'}

    def _global_revision(self) -> int:
        row = self.connection.execute(
            'SELECT value FROM metadata WHERE key = ?', ('global_revision',)
        ).fetchone()
        return row['value']

    def _current_article(self, slug: str) -> Tuple[Dict[str, Any], int]:
        row = self.connection.execute(
            '''SELECT content_json, created_seq FROM article_versions
               WHERE slug = ? AND valid_to_revision IS NULL''',
            (slug,),
        ).fetchone()
        if row is None:
            raise KeyError(slug)
        article = json.loads(row['content_json'])
        article['created_seq'] = row['created_seq']
        return article, row['created_seq']

    def commit(self, mutation: Mapping[str, Any], at_ms: int) -> CommitRecord:
        if not isinstance(at_ms, int) or isinstance(at_ms, bool) or at_ms < 0:
            raise ValueError('at_ms must be a non-negative integer')
        if not isinstance(mutation, Mapping):
            raise ValueError('mutation must be a mapping')
        operation = mutation.get('operation')
        if operation not in {'create', 'update', 'delete'}:
            raise ValueError('operation must be create, update or delete')

        with self.lock:
            revision = self._global_revision() + 1
            if operation == 'create':
                article = self._prepare_create(mutation, at_ms)
                slug = article['slug']
                if self.connection.execute(
                    'SELECT 1 FROM article_versions WHERE slug = ? AND valid_to_revision IS NULL',
                    (slug,),
                ).fetchone():
                    raise ValueError('article slug already exists')
                previous_tags = []
            else:
                slug = mutation.get('slug')
                if not isinstance(slug, str) or not slug:
                    raise ValueError('slug must be a non-empty string')
                current, _ = self._current_article(slug)
                previous_tags = list(current['tagList'])
                article = None if operation == 'delete' else self._prepare_update(current, mutation, at_ms)

            with self.connection:
                if operation in {'update', 'delete'}:
                    self.connection.execute(
                        '''UPDATE article_versions SET valid_to_revision = ?
                           WHERE slug = ? AND valid_to_revision IS NULL''',
                        (revision, slug),
                    )
                if article is not None:
                    self.connection.execute(
                        '''INSERT INTO article_versions
                           (slug, valid_from_revision, valid_to_revision, created_seq, content_json)
                           VALUES (?, ?, NULL, ?, ?)''',
                        (
                            slug, revision, article['created_seq'],
                            _encoded(self._public(article)).decode('utf-8'),
                        ),
                    )
                self.connection.execute(
                    'UPDATE metadata SET value = ? WHERE key = ?',
                    (revision, 'global_revision'),
                )

            public = self._public(article) if article is not None else None
            return CommitRecord(
                revision=revision,
                committed_at_ms=at_ms,
                affected_keys=(slug,),
                notification_payload={
                    'operation': operation,
                    'slug': slug,
                    'revision': revision,
                    'previous_tags': previous_tags,
                    'current_tags': list(article['tagList']) if article is not None else [],
                    'content': public,
                    'content_sha256': content_hash(public) if public is not None else None,
                },
            )

    def _prepare_create(self, mutation: Mapping[str, Any], at_ms: int) -> Dict[str, Any]:
        supplied = mutation.get('article')
        if not isinstance(supplied, Mapping):
            raise ValueError('create requires an article mapping')
        required = {'slug', 'title', 'description', 'body', 'tagList'}
        if not required.issubset(supplied):
            raise ValueError(f'create article requires fields: {sorted(required)}')
        unknown = set(supplied) - required - {'created_seq', 'favoritesCount'}
        if unknown:
            raise ValueError(f'unsupported create fields: {sorted(unknown)}')
        article = {
            **self._fixture_article(0, 0),
            **dict(supplied),
            'createdAt': _time_string(at_ms),
            'updatedAt': _time_string(at_ms),
            'created_seq': supplied.get('created_seq', self.article_count + self._global_revision()),
        }
        self._validate_article(article)
        return article

    def _prepare_update(
        self, current: Mapping[str, Any], mutation: Mapping[str, Any], at_ms: int
    ) -> Dict[str, Any]:
        changes = mutation.get('changes')
        if not isinstance(changes, Mapping) or not changes:
            raise ValueError('update requires a non-empty changes mapping')
        unknown = set(changes) - UPDATE_FIELDS
        if unknown:
            raise ValueError(f'unsupported update fields: {sorted(unknown)}')
        article = dict(current)
        article.update(changes)
        article['updatedAt'] = _time_string(at_ms)
        self._validate_article(article)
        return article

    @staticmethod
    def _validate_article(article: Mapping[str, Any]) -> None:
        for field in ('slug', 'title', 'description', 'body'):
            if not isinstance(article.get(field), str) or not article[field]:
                raise ValueError(f'{field} must be a non-empty string')
        tags = article.get('tagList')
        if (
            not isinstance(tags, list) or not tags or any(tag not in ALLOWED_TAGS for tag in tags)
            or len(tags) != len(set(tags))
        ):
            raise ValueError(f'tagList must contain unique declared tags: {ALLOWED_TAGS}')
        created_seq = article.get('created_seq')
        if not isinstance(created_seq, int) or isinstance(created_seq, bool) or created_seq < 0:
            raise ValueError('created_seq must be a non-negative integer')
        favorites = article.get('favoritesCount')
        if not isinstance(favorites, int) or isinstance(favorites, bool) or favorites < 0:
            raise ValueError('favoritesCount must be a non-negative integer')

    def _query_at(self, revision: int, tag: Optional[str], limit: int, offset: int) -> Dict[str, Any]:
        rows = self.connection.execute(
            '''SELECT content_json, created_seq FROM article_versions
               WHERE valid_from_revision <= ?
                 AND (valid_to_revision IS NULL OR valid_to_revision > ?)''',
            (revision, revision),
        ).fetchall()
        articles = []
        for row in rows:
            article = json.loads(row['content_json'])
            if tag is None or tag in article['tagList']:
                articles.append((row['created_seq'], article['slug'], article))
        articles.sort(key=lambda item: (item[0], item[1]), reverse=True)
        public = [item[2] for item in articles]
        return {'articles': public[offset:offset + limit], 'articlesCount': len(public)}

    def read(self, key_or_query: str, validator: Optional[str] = None) -> ReadRecord:
        _, tag, limit, offset = parse_feed_query(key_or_query)
        with self.lock:
            revision = self._global_revision()
            content = self._query_at(revision, tag, limit, offset)
        digest = content_hash(content)
        current_validator = f'"feed:{digest}"'
        not_modified = validator == current_validator
        return ReadRecord(
            decision_revision=revision,
            served_revision=revision,
            content=content,
            content_sha256=digest,
            validator=current_validator,
            origin_read=True,
            response_body_bytes=0 if not_modified else len(_encoded(content)),
            not_modified=not_modified,
        )

    def oracle(self, key_or_query: str, decision_revision: int) -> OracleSnapshot:
        if not isinstance(decision_revision, int) or isinstance(decision_revision, bool) or decision_revision < 0:
            raise ValueError('decision_revision must be a non-negative integer')
        _, tag, limit, offset = parse_feed_query(key_or_query)
        with self.lock:
            if decision_revision > self._global_revision():
                raise KeyError(decision_revision)
            content = self._query_at(decision_revision, tag, limit, offset)
        return OracleSnapshot(
            decision_revision=decision_revision,
            content=content,
            content_sha256=content_hash(content),
        )
