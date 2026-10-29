"""No-fault Redis Pub/Sub and Streams delivery calibration.

This is an engineering tool. It records transport delivery timings and a host
manifest, but it does not execute application workloads or collect study data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import queue
import socket
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


class RedisError(RuntimeError):
    pass


class RESPConnection:
    def __init__(self, host: str, port: int, timeout_s: float = 5.0) -> None:
        self.socket = socket.create_connection((host, port), timeout=timeout_s)
        self.socket.settimeout(timeout_s)
        self.stream = self.socket.makefile('rb')

    def close(self) -> None:
        try:
            self.stream.close()
        finally:
            self.socket.close()

    @staticmethod
    def encode_command(parts: Sequence[Any]) -> bytes:
        encoded = [f'*{len(parts)}\r\n'.encode('ascii')]
        for part in parts:
            value = part if isinstance(part, bytes) else str(part).encode('utf-8')
            encoded.extend((f'${len(value)}\r\n'.encode('ascii'), value, b'\r\n'))
        return b''.join(encoded)

    def send_command(self, *parts: Any) -> None:
        self.socket.sendall(self.encode_command(parts))

    def command(self, *parts: Any) -> Any:
        self.send_command(*parts)
        return self.read_response()

    def read_response(self) -> Any:
        marker = self.stream.read(1)
        if not marker:
            raise RedisError('Redis connection closed')
        line = self.stream.readline()
        if not line.endswith(b'\r\n'):
            raise RedisError('malformed RESP line')
        body = line[:-2]
        if marker == b'+':
            return body
        if marker == b'-':
            raise RedisError(body.decode('utf-8', errors='replace'))
        if marker == b':':
            return int(body)
        if marker == b'$':
            length = int(body)
            if length == -1:
                return None
            value = self.stream.read(length)
            if len(value) != length or self.stream.read(2) != b'\r\n':
                raise RedisError('malformed RESP bulk string')
            return value
        if marker == b'*':
            length = int(body)
            if length == -1:
                return None
            return [self.read_response() for _ in range(length)]
        raise RedisError(f'unsupported RESP marker: {marker!r}')


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _percentile(values: Sequence[int], probability: float) -> int:
    if not values:
        raise ValueError('percentile requires values')
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(probability * len(ordered) + 0.999999) - 1))
    return ordered[index]


def summarize(latencies_ns: Sequence[int]) -> Dict[str, Any]:
    if not latencies_ns or any(value < 0 for value in latencies_ns):
        raise ValueError('latencies must be non-empty and non-negative')
    median = int(statistics.median(latencies_ns))
    return {
        'count': len(latencies_ns),
        'min_ns': min(latencies_ns),
        'p50_ns': _percentile(latencies_ns, 0.50),
        'p90_ns': _percentile(latencies_ns, 0.90),
        'p95_ns': _percentile(latencies_ns, 0.95),
        'p99_ns': _percentile(latencies_ns, 0.99),
        'max_ns': max(latencies_ns),
        'median_absolute_deviation_ns': int(
            statistics.median(abs(value - median) for value in latencies_ns)
        ),
    }


def _decode_payload(payload: bytes) -> tuple[int, int]:
    sequence, sent_ns = payload.decode('ascii').split('|', 1)
    return int(sequence), int(sent_ns)


def calibrate_pubsub(
    host: str, port: int, warmup: int, samples: int
) -> Dict[str, Any]:
    channel = 'freshness:engineering:pubsub'
    subscriber = RESPConnection(host, port)
    publisher = RESPConnection(host, port)
    subscriber.command('SUBSCRIBE', channel)
    received: queue.Queue = queue.Queue()
    errors: queue.Queue = queue.Queue()
    total = warmup + samples

    def reader() -> None:
        try:
            for _ in range(total):
                response = subscriber.read_response()
                if not isinstance(response, list) or len(response) != 3 or response[0] != b'message':
                    raise RedisError(f'unexpected Pub/Sub response: {response!r}')
                sequence, sent_ns = _decode_payload(response[2])
                received.put((sequence, time.perf_counter_ns() - sent_ns))
        except Exception as error:
            errors.put(error)

    thread = threading.Thread(target=reader, name='redis-pubsub-reader', daemon=True)
    thread.start()
    latencies: List[int] = []
    try:
        for sequence in range(total):
            sent_ns = time.perf_counter_ns()
            listeners = publisher.command('PUBLISH', channel, f'{sequence}|{sent_ns}')
            if listeners != 1:
                raise RedisError(f'expected one Pub/Sub listener, got {listeners}')
            observed_sequence, latency_ns = received.get(timeout=5)
            if observed_sequence != sequence:
                raise RedisError(
                    f'Pub/Sub sequence mismatch: expected {sequence}, got {observed_sequence}'
                )
            latencies.append(latency_ns)
        thread.join(timeout=5)
        if thread.is_alive():
            raise RedisError('Pub/Sub reader did not terminate')
        if not errors.empty():
            raise errors.get()
    finally:
        subscriber.close()
        publisher.close()
    retained = latencies[warmup:]
    return {'summary': summarize(retained), 'latencies_ns': retained}


def _stream_payload(response: Any) -> tuple[bytes, bytes]:
    try:
        entries = response[0][1]
        fields = entries[0][1]
        values = {fields[index]: fields[index + 1] for index in range(0, len(fields), 2)}
        return values[b'sequence'], values[b'sent_ns']
    except (IndexError, KeyError, TypeError) as error:
        raise RedisError(f'unexpected Streams response: {response!r}') from error


def calibrate_streams(
    host: str, port: int, warmup: int, samples: int
) -> Dict[str, Any]:
    stream_key = 'freshness:engineering:stream'
    reader_connection = RESPConnection(host, port)
    writer = RESPConnection(host, port)
    writer.command('DEL', stream_key)
    last_id = writer.command('XADD', stream_key, '*', 'sequence', '-1', 'sent_ns', '0')
    received: queue.Queue = queue.Queue()
    errors: queue.Queue = queue.Queue()
    total = warmup + samples

    def reader() -> None:
        nonlocal last_id
        try:
            for _ in range(total):
                response = reader_connection.command(
                    'XREAD', 'COUNT', 1, 'BLOCK', 5000, 'STREAMS', stream_key, last_id,
                )
                if response is None:
                    raise RedisError('Streams reader timed out')
                sequence, sent_ns = _stream_payload(response)
                last_id = response[0][1][0][0]
                received.put((int(sequence), time.perf_counter_ns() - int(sent_ns)))
        except Exception as error:
            errors.put(error)

    thread = threading.Thread(target=reader, name='redis-stream-reader', daemon=True)
    thread.start()
    latencies: List[int] = []
    try:
        for sequence in range(total):
            sent_ns = time.perf_counter_ns()
            writer.command(
                'XADD', stream_key, '*', 'sequence', sequence, 'sent_ns', sent_ns,
            )
            observed_sequence, latency_ns = received.get(timeout=5)
            if observed_sequence != sequence:
                raise RedisError(
                    f'Streams sequence mismatch: expected {sequence}, got {observed_sequence}'
                )
            latencies.append(latency_ns)
        thread.join(timeout=5)
        if thread.is_alive():
            raise RedisError('Streams reader did not terminate')
        if not errors.empty():
            raise errors.get()
    finally:
        reader_connection.close()
        writer.close()
    retained = latencies[warmup:]
    return {'summary': summarize(retained), 'latencies_ns': retained}


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def _wait_for_redis(port: int, process: subprocess.Popen) -> None:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError('redis-server exited during startup')
        try:
            connection = RESPConnection('127.0.0.1', port, timeout_s=0.2)
            try:
                if connection.command('PING') == b'PONG':
                    return
            finally:
                connection.close()
        except (OSError, RedisError):
            time.sleep(0.02)
    raise RuntimeError('redis-server did not become ready')


def _redis_version(executable: str) -> str:
    return subprocess.run(
        [executable, '--version'], check=True, capture_output=True, text=True,
    ).stdout.strip()


def collect(output: Path, redis_server: str, warmup: int, samples: int) -> None:
    if warmup < 1 or samples < 10:
        raise ValueError('warmup must be positive and samples must be at least 10')
    port = _free_port()
    command = [
        redis_server,
        '--bind', '127.0.0.1',
        '--port', str(port),
        '--save', '',
        '--appendonly', 'no',
        '--protected-mode', 'yes',
        '--loglevel', 'warning',
    ]
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    try:
        _wait_for_redis(port, process)
        pubsub = calibrate_pubsub('127.0.0.1', port, warmup, samples)
        streams = calibrate_streams('127.0.0.1', port, warmup, samples)
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    artifact = {
        'artifact_schema_version': 1,
        'measurement_kind': 'no-fault-transport-engineering-calibration',
        'contains_application_study_observations': False,
        'protocol_status': 'pre-freeze-v0.3-do-not-use-as-study-data',
        'clock': 'time.perf_counter_ns',
        'warmup_messages_per_mode': warmup,
        'retained_messages_per_mode': samples,
        'redis_configuration': command[1:],
        'host_manifest': {
            'platform': platform.platform(),
            'uname': tuple(platform.uname()),
            'logical_cpu_count': os.cpu_count(),
            'python': sys.version,
            'redis': _redis_version(redis_server),
        },
        'source_sha256': _sha256(Path(__file__)),
        'modes': {'redis-pubsub': pubsub, 'redis-streams': streams},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(artifact, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    parser.add_argument('--redis-server', default='redis-server')
    parser.add_argument('--warmup', type=int, default=100)
    parser.add_argument('--samples', type=int, default=1000)
    args = parser.parse_args()
    collect(args.output, args.redis_server, args.warmup, args.samples)


if __name__ == '__main__':
    main()
