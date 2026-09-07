"""Fixed, stdin-only media probing with bounded resources and no network protocol."""

from __future__ import annotations

import json
import os
import resource
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Any, Callable

from api.services.media_library_processor import normalize_probe


MAX_INPUT_BYTES = 100 * 1024 * 1024
MAX_OUTPUT_BYTES = 64 * 1024


class MediaParserError(ValueError):
    pass


@dataclass(frozen=True)
class ParserExecution:
    argv: tuple[str, ...]
    timeout_seconds: int
    maximum_output_bytes: int


FFPROBE_EXECUTION = ParserExecution(
    (
        '/usr/bin/ffprobe',
        '-v',
        'error',
        '-protocol_whitelist',
        'pipe',
        '-show_entries',
        'format=duration:stream=codec_type,width,height',
        '-of',
        'json',
        '-i',
        'pipe:0',
    ),
    20,
    MAX_OUTPUT_BYTES,
)


def _resource_limits() -> None:
    resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_OUTPUT_BYTES, MAX_OUTPUT_BYTES))


def execute_fixed_parser(
    content: bytes,
    *,
    execution: ParserExecution = FFPROBE_EXECUTION,
    runner: Callable[..., subprocess.CompletedProcess[bytes]] | None = None,
) -> dict[str, Any]:
    if not isinstance(content, bytes) or not 1 <= len(content) <= MAX_INPUT_BYTES:
        raise MediaParserError('media_parser_input_invalid')
    if execution != FFPROBE_EXECUTION:
        raise MediaParserError('media_parser_contract_invalid')
    try:
        if runner is not None:
            completed = runner(
                list(execution.argv), input=content, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, timeout=execution.timeout_seconds, check=False,
                shell=False, close_fds=True, cwd='/',
                env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C', 'HOME': '/nonexistent'},
                preexec_fn=_resource_limits if os.name == 'posix' else None,
            )
            stdout = bytes(completed.stdout or b'')
            stderr = bytes(completed.stderr or b'')
        else:
            with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
                completed = subprocess.run(
                    list(execution.argv), input=content, stdout=output, stderr=errors,
                    timeout=execution.timeout_seconds, check=False, shell=False,
                    close_fds=True, cwd='/',
                    env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C', 'HOME': '/nonexistent'},
                    preexec_fn=_resource_limits if os.name == 'posix' else None,
                )
                output.seek(0)
                errors.seek(0)
                stdout = output.read(execution.maximum_output_bytes + 1)
                stderr = errors.read(4097)
    except (OSError, subprocess.SubprocessError) as exc:
        raise MediaParserError('media_parser_unavailable') from exc
    if completed.returncode != 0 or len(stdout) > execution.maximum_output_bytes or len(stderr) > 4096:
        raise MediaParserError('media_parser_rejected')
    try:
        payload = json.loads(stdout)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MediaParserError('media_parser_response_invalid') from exc
    if not isinstance(payload, dict) or set(payload) not in (
        {'format', 'streams'},
        {'format', 'streams', 'programs', 'stream_groups'},
    ):
        raise MediaParserError('media_parser_response_invalid')
    if payload.get('programs', []) != [] or payload.get('stream_groups', []) != []:
        raise MediaParserError('media_parser_response_invalid')
    streams = payload['streams']
    values = payload['format']
    if not isinstance(streams, list) or not 1 <= len(streams) <= 16 or not isinstance(values, dict):
        raise MediaParserError('media_parser_response_invalid')
    duration_value = values.get('duration')
    try:
        duration = float(duration_value) if duration_value is not None else None
    except (TypeError, ValueError) as exc:
        raise MediaParserError('media_parser_response_invalid') from exc
    videos = [item for item in streams if isinstance(item, dict) and item.get('codec_type') == 'video']
    width = videos[0].get('width') if videos else None
    height = videos[0].get('height') if videos else None
    return {
        'durationSeconds': duration,
        'width': width,
        'height': height,
        'streamCount': len(streams),
    }


def probe_media_no_network(
    content: bytes,
    media_type: str,
    *,
    runner: Callable[..., subprocess.CompletedProcess[bytes]] | None = None,
):
    raw = execute_fixed_parser(content, runner=runner)
    return normalize_probe(
        {'mediaType': media_type, **raw},
        expected_type=media_type,
        tool_ref='ffprobe:bounded-v1',
    )
