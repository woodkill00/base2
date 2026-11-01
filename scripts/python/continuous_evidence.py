"""Strict synthetic continuous viewport receipts; incomplete runs remain incomplete."""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

NAME = re.compile(r'continuous-([a-z0-9-]{1,90})\.json')
FRAME = re.compile(r'current-continuous-[a-z0-9-]{1,90}-(?:[0-9]{3}|focus)\.png')
BUDGET = 128 * 1024
ERRORS = {'empty', 'limit', 'index', 'route', 'extent', 'geometry', 'gap', 'nonprogress',
          'overlap', 'incomplete', 'end-not-reached', 'capture-or-validation-failed',
          'focus-not-neutral', 'skip-overlay-visible', 'focus-restore-failed'}


def _validate(raw: bytes, path: Path, commit: str, tree: str, project: str | None = None, run: str | None = None, attempt: str | None = None) -> dict:
    def require(condition: bool) -> None:
        if not condition:
            raise ValueError('invalid continuous evidence')

    def unique(pairs: list) -> dict:
        result = {}
        for key, value in pairs:
            require(key not in result)
            result[key] = value
        return result

    require(len(raw) <= BUDGET and bool(NAME.fullmatch(path.name)))
    data = json.loads(raw, object_pairs_hook=unique)
    require(isinstance(data, dict))
    version = data.get('schemaVersion')
    require(type(version) is int and version in (1, 2))
    extra = {'coverageKind', 'unobscuredReview', 'focus'} if version == 2 else set()
    require(set(data) == extra | {'schemaVersion', 'fixtureScope', 'scope', 'sourceCommit', 'sourceTree',
                         'runId', 'attempt', 'project', 'test', 'route', 'state', 'target', 'extent',
                         'segmentLimit', 'reachedEnd', 'complete', 'errors', 'segments'})
    require(data['fixtureScope'] == 'synthetic-project-tests')
    require(data['scope'] == 'Diagnostic continuous viewports; not visual acceptance.')
    require(data['sourceCommit'] == commit and data['sourceTree'] == tree)
    require(bool(re.fullmatch('[0-9a-f]{40}', commit)) and bool(re.fullmatch('[0-9a-f]{40}', tree)))
    match = NAME.fullmatch(path.name)
    assert match is not None
    require(data['state'] == match.group(1))
    require(bool(re.fullmatch(r'/[a-zA-Z0-9/_-]*', data['route'])))
    require(bool(re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', data['project'])))
    require(project is None or project == data['project'])
    require(isinstance(data['test'], str) and 0 < len(data['test']) <= 200 and '\n' not in data['test'])
    require(all(isinstance(data[k], str) and bool(re.fullmatch('[0-9]{1,20}', data[k])) for k in ('runId', 'attempt')))
    require(run is None or data['runId'] == run)
    require(attempt is None or data['attempt'] == attempt)
    require(data['target'] in {'dialog', 'content-scrollport'})
    require(type(data['complete']) is bool and type(data['reachedEnd']) is bool and data['segmentLimit'] == 64)
    require(isinstance(data['errors'], list) and len(data['errors']) == len(set(data['errors'])) and set(data['errors']) <= ERRORS)
    require(isinstance(data['segments'], list) and len(data['segments']) <= 64)

    def number(value: Any) -> bool:
        return type(value) in {int, float} and math.isfinite(value) and abs(value) <= 1_000_000

    def image_identity(row: dict, name: str) -> None:
        require(set(row) == {'file', 'sha256', 'bytes'})
        require(row['file'] == name and bool(FRAME.fullmatch(name)))
        require(bool(re.fullmatch('[0-9a-f]{64}', row['sha256'])))
        require(type(row['bytes']) is int and 0 < row['bytes'] <= 28 * 1024 * 1024)
        image = path.parent / name
        require(not any(p.is_symlink() for p in (image, *image.parents)))
        require(image.is_file() and image.stat().st_size == row['bytes'])
        raw_image = image.read_bytes()
        require(raw_image.startswith(b'\x89PNG\r\n\x1a\n') and hashlib.sha256(raw_image).hexdigest() == row['sha256'])

    if version == 2:
        require(data['coverageKind'] == 'neutral-focus-geometric' and data['unobscuredReview'] == 'required')
        focus = data['focus']
        require(isinstance(focus, dict) and set(focus) == {'mode', 'originalHadFocus', 'restored', 'capture'})
        require(focus['mode'] == 'neutral-content' and type(focus['originalHadFocus']) is bool and type(focus['restored']) is bool)
        if focus['capture'] is not None:
            image_identity(focus['capture'], f"current-continuous-{data['state']}-focus.png")
        require(not data['complete'] or (focus['restored'] and focus['capture'] is not None))

    require(number(data['extent']))
    end, offset, previous_height = 0.0, -1.0, 0.0
    coverage = True
    for index, row in enumerate(data['segments']):
        require(set(row) == ({'neutralFocus', 'skipOverlayClear'} if version == 2 else set()) | {'index', 'route', 'start', 'end', 'extent', 'offset', 'file', 'sha256', 'bytes', 'height', 'inset', 'scale', 'max', 'viewport', 'rect'})
        if version == 2:
            require(type(row['neutralFocus']) is bool and type(row['skipOverlayClear']) is bool)
            coverage = coverage and row['neutralFocus'] and row['skipOverlayClear']
        require(row['index'] == index and row['file'] == f"current-continuous-{data['state']}-{index:03d}.png")
        require(bool(FRAME.fullmatch(row['file'])) and bool(re.fullmatch('[0-9a-f]{64}', row['sha256'])))
        require(all(number(row[k]) for k in ('start', 'end', 'extent', 'offset', 'height', 'inset', 'scale', 'max')))
        require(isinstance(row['viewport'], list) and len(row['viewport']) == 3 and all(number(v) and v > 0 for v in row['viewport']))
        require(isinstance(row['rect'], list) and len(row['rect']) == 4 and all(type(v) in {int, float} and math.isfinite(v) and abs(v) <= 1_000_000 for v in row['rect']))
        require(row['scale'] > 0 and type(row['bytes']) is int and 0 < row['bytes'] <= 28 * 1024 * 1024)
        require(bool(re.fullmatch(r'/[a-zA-Z0-9/_-]*', row['route'])))
        image = path.parent / row['file']
        require(not any(p.is_symlink() for p in (image, *image.parents)))
        require(image.is_file() and image.stat().st_size == row['bytes'])
        content = image.read_bytes()
        require(content.startswith(b'\x89PNG\r\n\x1a\n') and hashlib.sha256(content).hexdigest() == row['sha256'])
        # CSS geometry uses a one-CSS-pixel rounding allowance. The bounding
        # rectangle includes up to two CSS pixels of border beyond clientHeight.
        # Recompute intervals rather than trusting a claimed complete union.
        x, y, width, rect_height = row['rect']
        viewport_width, viewport_height, _ = row['viewport']
        height, inset, scale = row['height'], row['inset'], row['scale']
        maximum, position = row['max'], row['offset']
        geometry_valid = (height > 0 and width > 0 and rect_height > 0
                          and 0 <= inset < height and maximum >= 0
                          and 0 <= position <= maximum + 1
                          and x >= -1 and x + width <= viewport_width + 1
                          and y < viewport_height and y + rect_height > 0
                          and -1 <= rect_height / scale - height <= 2)
        if geometry_valid:
            derived_extent = maximum + height - inset
            derived_start = position + max(inset, (max(y, 0) - y) / scale) - inset
            derived_end = min(maximum + height,
                              position + (min(y + rect_height, viewport_height) - y) / scale) - inset
            require(abs(row['extent'] - derived_extent) <= 1)
            require(abs(row['start'] - derived_start) <= 1)
            require(abs(row['end'] - derived_end) <= 1)
        coverage = coverage and geometry_valid
        coverage = coverage and row['height'] > 0 and row['start'] >= 0 and row['extent'] >= 0
        coverage = coverage and row['route'] == data['route'] and row['extent'] == data['extent']
        coverage = coverage and row['start'] <= end + 1 and row['end'] > row['start'] and row['end'] <= data['extent'] + 1
        coverage = coverage and (index == 0 or (row['offset'] > offset and row['end'] > end and row['start'] <= end - previous_height * 0.25 + 1))
        previous_height = row['end'] - row['start']
        end, offset = max(end, row['end']), row['offset']
    if data['complete']:
        require(bool(data['segments']) and coverage and end >= data['extent'] - 1 and data['reachedEnd'] and not data['errors'])
        require(abs(data['segments'][-1]['offset'] - data['segments'][-1]['max']) <= 1)
    else:
        require(bool(data['errors']))
    return data


def capture_rows(data: dict) -> list:
    """Focus context is retained separately and never contributes to coverage."""
    context = data.get('focus', {}).get('capture')
    return data['segments'] + ([context] if context is not None else [])


def validate(raw: bytes, path: Path, commit: str, tree: str, project: str | None = None,
             run: str | None = None, attempt: str | None = None) -> dict:
    """Normalize malformed JSON shapes without swallowing IO or programming failures."""
    try:
        return _validate(raw, path, commit, tree, project, run, attempt)
    except (TypeError, KeyError, AttributeError, IndexError, OverflowError) as exc:
        raise ValueError("invalid continuous evidence shape") from exc
