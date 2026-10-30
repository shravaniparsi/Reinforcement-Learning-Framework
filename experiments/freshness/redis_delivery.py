"""Real Redis notification delivery for instrumented freshness traces."""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Optional

from .redis_calibration import RESPConnection, RedisError, _free_port, _wait_for_redis


@dataclass(frozen=True)
class TransportDelivery:
    notification_id: str
    mode: str
    payload_bytes: int
    wall_ns: int
    thread_cpu_ns: int

    def to_mapping(self) -> Mapping[str, Any]:
        return asdict(self)


class RedisNotificationTransport:
    """Start an isolated Redis server and synchronously deliver notifications."""

    def __init__(self, mode: str, redis_server: str = 'redis-server') -> None:
        if mode not in {'redis-pubsub', 'redis-streams'}:
            raise ValueError('unsupported Redis notification mode')
        self.mode = mode
        self.port = _free_port()
        self.channel = 'freshness:trace:notifications'
        self.stream_key = 'freshness:trace:notifications'
        self.process = subprocess.Popen(
            [
                redis_server, '--bind', '127.0.0.1', '--port', str(self.port),
                '--save', '', '--appendonly', 'no', '--protected-mode', 'yes',
                '--loglevel', 'warning',
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        self.publisher: Optional[RESPConnection] = None
        self.receiver: Optional[RESPConnection] = None
        self.last_stream_id: Any = b'0-0'
        try:
            _wait_for_redis(self.port, self.process)
            self.publisher = RESPConnection('127.0.0.1', self.port)
            self.receiver = RESPConnection('127.0.0.1', self.port)
            if self.mode == 'redis-pubsub':
                response = self.receiver.command('SUBSCRIBE', self.channel)
                if not isinstance(response, list) or response[:2] != [b'subscribe', self.channel.encode()]:
                    raise RedisError('unexpected Pub/Sub subscription response')
            else:
                self.publisher.command('DEL', self.stream_key)
        except Exception:
            self.close()
            raise

    def reset(self) -> None:
        if self.publisher is None:
            raise RuntimeError('Redis transport is closed')
        if self.mode == 'redis-streams':
            self.publisher.command('DEL', self.stream_key)
            self.last_stream_id = b'0-0'

    @staticmethod
    def _payload(notification_id: str, key: str, payload: Mapping[str, Any]) -> bytes:
        return json.dumps(
            {'notification_id': notification_id, 'key': key, 'payload': payload},
            sort_keys=True,
            separators=(',', ':'),
            ensure_ascii=False,
            allow_nan=False,
        ).encode('utf-8')

    def deliver(
        self, notification_id: str, key: str, payload: Mapping[str, Any]
    ) -> TransportDelivery:
        if self.publisher is None or self.receiver is None:
            raise RuntimeError('Redis transport is closed')
        encoded = self._payload(notification_id, key, payload)
        wall_start = time.perf_counter_ns()
        cpu_start = time.thread_time_ns()
        if self.mode == 'redis-pubsub':
            listeners = self.publisher.command('PUBLISH', self.channel, encoded)
            response = self.receiver.read_response()
            if listeners != 1 or not isinstance(response, list) or len(response) != 3:
                raise RedisError('unexpected Pub/Sub delivery response')
            observed = response[2]
        else:
            self.publisher.command('XADD', self.stream_key, '*', 'payload', encoded)
            response = self.receiver.command(
                'XREAD', 'COUNT', 1, 'BLOCK', 5000,
                'STREAMS', self.stream_key, self.last_stream_id,
            )
            if response is None:
                raise RedisError('Streams delivery timed out')
            try:
                entry = response[0][1][0]
                self.last_stream_id = entry[0]
                fields = entry[1]
                values = {fields[index]: fields[index + 1] for index in range(0, len(fields), 2)}
                observed = values[b'payload']
            except (IndexError, KeyError, TypeError) as error:
                raise RedisError('unexpected Streams delivery response') from error
        cpu_ns = time.thread_time_ns() - cpu_start
        wall_ns = time.perf_counter_ns() - wall_start
        if observed != encoded:
            raise RedisError('Redis notification payload changed in transit')
        return TransportDelivery(notification_id, self.mode, len(encoded), wall_ns, cpu_ns)

    def close(self) -> None:
        for connection in (self.receiver, self.publisher):
            if connection is not None:
                try:
                    connection.close()
                except OSError:
                    pass
        self.receiver = None
        self.publisher = None
        process = getattr(self, 'process', None)
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        if process is not None and process.stdout is not None:
            process.stdout.close()

    def __enter__(self) -> 'RedisNotificationTransport':
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
