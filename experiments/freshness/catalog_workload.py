"""Deterministic SQLite workload for mutable product detail responses."""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Mapping, Optional

from .workload import CommitRecord, OracleSnapshot, ReadRecord, content_hash


ALLOWED_FIELDS = frozenset({'name', 'description', 'price_cents', 'available'})


def _encoded(content: Any) -> bytes:
    return json.dumps(
        content, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
        allow_nan=False,
    ).encode('utf-8')


class CatalogWorkload:
    workload_id = 'mutable-product-v1'

    def __init__(self, product_count: int = 100) -> None:
        if not isinstance(product_count, int) or isinstance(product_count, bool) or product_count < 2:
            raise ValueError('product_count must be an integer of at least 2')
        self.product_count = product_count
        self.connection = sqlite3.connect(':memory:')
        self.connection.row_factory = sqlite3.Row
        self.reset(seed=0)

    def close(self) -> None:
        self.connection.close()

    def reset(self, seed: int) -> None:
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise ValueError('seed must be an integer')
        cursor = self.connection.cursor()
        cursor.executescript(
            '''
            DROP TABLE IF EXISTS metadata;
            DROP TABLE IF EXISTS products;
            DROP TABLE IF EXISTS product_history;
            CREATE TABLE metadata (
                key TEXT PRIMARY KEY,
                value INTEGER NOT NULL
            );
            CREATE TABLE products (
                product_id TEXT PRIMARY KEY,
                object_revision INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                price_cents INTEGER NOT NULL CHECK (price_cents >= 0),
                available INTEGER NOT NULL CHECK (available IN (0, 1))
            );
            CREATE TABLE product_history (
                product_id TEXT NOT NULL,
                object_revision INTEGER NOT NULL,
                committed_at_ms INTEGER NOT NULL,
                content_json TEXT NOT NULL,
                PRIMARY KEY (product_id, object_revision)
            );
            '''
        )
        cursor.execute('INSERT INTO metadata (key, value) VALUES (?, ?)', ('seed', seed))
        for index in range(1, self.product_count + 1):
            product_id = f'product-{index}'
            product = {
                'id': product_id,
                'name': f'Desk accessory {index:03d}',
                'description': 'A compact accessory for an organized workspace.',
                'price_cents': 1200 + index * 37 + seed % 17,
                'available': (index + seed) % 7 != 0,
                'revision': 0,
            }
            cursor.execute(
                '''INSERT INTO products
                   (product_id, object_revision, name, description, price_cents, available)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (
                    product_id, 0, product['name'], product['description'],
                    product['price_cents'], int(product['available']),
                ),
            )
            cursor.execute(
                '''INSERT INTO product_history
                   (product_id, object_revision, committed_at_ms, content_json)
                   VALUES (?, ?, ?, ?)''',
                (product_id, 0, 0, _encoded(product).decode('utf-8')),
            )
        self.connection.commit()

    def _current(self, product_id: str) -> Mapping[str, Any]:
        row = self.connection.execute(
            '''SELECT product_id, object_revision, name, description, price_cents, available
               FROM products WHERE product_id = ?''',
            (product_id,),
        ).fetchone()
        if row is None:
            raise KeyError(product_id)
        return {
            'id': row['product_id'],
            'name': row['name'],
            'description': row['description'],
            'price_cents': row['price_cents'],
            'available': bool(row['available']),
            'revision': row['object_revision'],
        }

    def commit(self, mutation: Mapping[str, Any], at_ms: int) -> CommitRecord:
        if not isinstance(at_ms, int) or isinstance(at_ms, bool) or at_ms < 0:
            raise ValueError('at_ms must be a non-negative integer')
        if not isinstance(mutation, Mapping):
            raise ValueError('mutation must be a mapping')
        product_id = mutation.get('key')
        changes = mutation.get('changes')
        if not isinstance(product_id, str) or not product_id:
            raise ValueError('mutation key must be a non-empty string')
        if not isinstance(changes, Mapping) or not changes:
            raise ValueError('mutation changes must be a non-empty mapping')
        unknown = set(changes) - ALLOWED_FIELDS
        if unknown:
            raise ValueError(f'unsupported product fields: {sorted(unknown)}')

        current = dict(self._current(product_id))
        updated = dict(current)
        updated.update(changes)
        self._validate_product(updated)
        updated['revision'] = current['revision'] + 1

        with self.connection:
            self.connection.execute(
                '''UPDATE products
                   SET object_revision = ?, name = ?, description = ?, price_cents = ?, available = ?
                   WHERE product_id = ?''',
                (
                    updated['revision'], updated['name'], updated['description'],
                    updated['price_cents'], int(updated['available']), product_id,
                ),
            )
            self.connection.execute(
                '''INSERT INTO product_history
                   (product_id, object_revision, committed_at_ms, content_json)
                   VALUES (?, ?, ?, ?)''',
                (
                    product_id, updated['revision'], at_ms,
                    _encoded(updated).decode('utf-8'),
                ),
            )

        return CommitRecord(
            revision=updated['revision'],
            committed_at_ms=at_ms,
            affected_keys=(product_id,),
            notification_payload={
                'key': product_id,
                'revision': updated['revision'],
                'content': updated,
                'content_sha256': content_hash(updated),
            },
        )

    @staticmethod
    def _validate_product(product: Mapping[str, Any]) -> None:
        if not isinstance(product['name'], str) or not product['name']:
            raise ValueError('name must be a non-empty string')
        if not isinstance(product['description'], str) or not product['description']:
            raise ValueError('description must be a non-empty string')
        price = product['price_cents']
        if not isinstance(price, int) or isinstance(price, bool) or price < 0:
            raise ValueError('price_cents must be a non-negative integer')
        if not isinstance(product['available'], bool):
            raise ValueError('available must be boolean')

    def read(self, key_or_query: str, validator: Optional[str] = None) -> ReadRecord:
        content = self._current(key_or_query)
        revision = content['revision']
        current_validator = f'"catalog:{key_or_query}:r{revision}"'
        not_modified = validator == current_validator
        encoded = _encoded(content)
        return ReadRecord(
            decision_revision=revision,
            served_revision=revision,
            content=content,
            content_sha256=content_hash(content),
            validator=current_validator,
            origin_read=True,
            response_body_bytes=0 if not_modified else len(encoded),
            not_modified=not_modified,
        )

    def oracle(self, key_or_query: str, decision_revision: int) -> OracleSnapshot:
        if not isinstance(decision_revision, int) or isinstance(decision_revision, bool) or decision_revision < 0:
            raise ValueError('decision_revision must be a non-negative integer')
        row = self.connection.execute(
            '''SELECT content_json FROM product_history
               WHERE product_id = ? AND object_revision = ?''',
            (key_or_query, decision_revision),
        ).fetchone()
        if row is None:
            raise KeyError((key_or_query, decision_revision))
        content = json.loads(row['content_json'])
        return OracleSnapshot(
            decision_revision=decision_revision,
            content=content,
            content_sha256=content_hash(content),
        )
