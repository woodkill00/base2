"""Strict numeric-only diagnostics for one synthetic WebKit workspace producer."""
import json
import math

from scripts.python import workspace_ownership

NAME = 'workspace-scroll-checkpoints.json'
BUDGET = 131072
PHASES = {'continuous-entry', 'continuous-footer-before', 'continuous-footer-after',
          'continuous-failed', 'continuous-cleanup', 'sample-entry',
          'sample-footer-before', 'sample-footer-after', 'sample-failed', 'sample-cleanup', 'capture-before', 'capture-after', 'sample-capture-before', 'sample-capture-after'}
STATES = {'current', 'workspace-records', 'workspace-schema', 'workspace-imports', 'workspace-exports'}


def registered(suite, relative):
    return (suite == 'workspace' and len(relative.parts) == 2 and relative.name == NAME
            and relative.parts[0].endswith('-webkit-mobile')
            and workspace_ownership.scenario_for_case(relative.parts[0]) in {'corpus', 'records-schema', 'imports-exports'})


def validate(raw, case=None):
    def require(ok):
        if not ok:
            raise ValueError('invalid workspace checkpoint')

    def number(value, low=0):
        require(type(value) in (int, float) and math.isfinite(value) and low <= value <= 100000000)

    def vector(value, size, nullable=False):
        if nullable and value is None:
            return
        require(type(value) is list and len(value) == size)
        for item in value:
            number(item, -100000000)
        if size in (4, 5):
            require(value[2] >= 0 and value[3] >= 0)
        if size == 5:
            require(value[4] > 0)

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result)
            result[key] = value
        return result

    require(len(raw) <= BUDGET)
    try:
        data = json.loads(raw, object_pairs_hook=unique_object)
    except (ValueError, UnicodeError) as error:
        raise ValueError('invalid workspace checkpoint') from error
    require(type(data) is dict and set(data) == {'schemaVersion', 'scope', 'incomplete', 'events'})
    require(type(data['schemaVersion']) is int and data['schemaVersion'] == 1)
    require(data['scope'] == 'synthetic-workspace-webkit' and type(data['incomplete']) is bool)
    require(type(data['events']) is list and len(data['events']) <= 192)
    require(bool(data['events']) or data['incomplete'])
    previous = 0
    for event in data['events']:
        require(type(event) is dict and set(event) == {'phase', 'state', 'index', 'focus', 'elapsedMs', 'phaseElapsedMs', 'errorCounts', 'route', 'activeState', 'target', 'targetCount', 'dialogCount', 'offset', 'max', 'viewport', 'visualViewport', 'targetRect', 'footerRect', 'headerRect'})
        require(type(event['phase']) is str and event['phase'] in PHASES)
        require(type(event['state']) is str and event['state'] in STATES)
        if case is not None:
            require(workspace_ownership.state_registered(case, event['state']))
        require(type(event['index']) is int and -1 <= event['index'] < 64)
        require(event['focus'] in ('neutral', 'tab', 'other'))
        require(event['route'] in ('workspace', 'other'))
        require(event['activeState'] in ('records', 'schema', 'imports', 'exports', 'unknown'))
        require(event['target'] in ('element', 'document', 'ambiguous'))
        for key in ('elapsedMs', 'phaseElapsedMs', 'max'):
            number(event[key])
        number(event['offset'], -100000000)  # Preserve native elastic overscroll honestly.
        require(event['elapsedMs'] >= previous)
        previous = event['elapsedMs']
        for key in ('targetCount', 'dialogCount'):
            require(type(event[key]) is int and 0 <= event[key] <= 1000)
        require(event['target'] == ('document' if event['targetCount'] == 0 else 'element' if event['targetCount'] == 1 else 'ambiguous'))
        counts = event['errorCounts']
        require(type(counts) is dict and set(counts) == {'total', 'timeout', 'comparison'})
        for count in counts.values():
            require(type(count) is int and 0 <= count <= 10000)
        require(counts['timeout'] <= counts['total'] and counts['comparison'] <= counts['total'])
        vector(event['viewport'], 2)
        require(all(v > 0 for v in event['viewport']))
        vector(event['visualViewport'], 5, True)
        for key in ('targetRect', 'footerRect', 'headerRect'):
            vector(event[key], 4, True)
    return data
