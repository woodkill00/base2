"""Allowlisted synthetic workspace lease/partial-frame diagnostics; never acceptance."""
import hashlib
import json
import re

NAME = 'workspace-capture-ownership.json'
BUDGET = 131072
PROJECTS = r'(?:chromium-(?:compact|phone-dpr3|landscape-touch|tablet|desktop|ultrawide|large-text|400-zoom|light|high-contrast)|firefox-desktop|webkit-mobile)'
CASES = {'corpus': 'workspace-release-workspac-d0657-ponsive-and-visually-stable',
         'selected': 'workspace-release-selected-9c572-aves-or-discards-explicitly',
         'vocabulary': 'workspace-release-synthet-'}
STATES = {'corpus': {'workspace-records', 'workspace-schema', 'workspace-imports', 'workspace-exports', 'current'},
          'selected': {'workspace-records-selected-edit', 'workspace-records-selected-saved', 'current'},
          'vocabulary': set()}
FRAME = re.compile(r'(?:current-continuous-(?:current|workspace-(?:records|schema|imports|exports|records-selected-edit|records-selected-saved))-(?:[0-9]{3}|focus)|current-scrollport-(?:(?:workspace-(?:records|schema|imports|exports|records-selected-edit|records-selected-saved))-)?(?:top|middle|footer)|workspace-(?:records|schema|imports|exports|records-selected-edit|records-selected-saved)-post-assert)\.png')


def registered(suite, relative):
    return (suite == 'workspace' and len(relative.parts) == 2 and relative.name == NAME
            and any(re.fullmatch(re.escape(prefix) + '-' + PROJECTS, relative.parts[0]) for kind, prefix in CASES.items() if kind != 'vocabulary'))


def validate(raw, path, provenance):
    def require(ok):
        if not ok:
            raise ValueError('invalid workspace ownership receipt')

    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result)
            result[key] = value
        return result

    require(len(raw) <= BUDGET)
    try:
        data = json.loads(raw, object_pairs_hook=unique)
    except (ValueError, UnicodeError) as error:
        raise ValueError('invalid workspace ownership receipt') from error
    require(type(data) is dict and set(data) == {'schemaVersion', 'scope', 'scenario', 'sourceCommit', 'sourceTree', 'runId', 'attempt', 'revoked', 'bodySettled', 'hookStarted', 'incomplete', 'coverage', 'errors', 'frames'})
    require(type(data['schemaVersion']) is int and data['schemaVersion'] == 1)
    require(data['scope'] == 'synthetic-workspace-ownership')
    require(type(data['scenario']) is str and data['scenario'] in {'corpus', 'selected'})
    require(re.fullmatch(re.escape(CASES[data['scenario']]) + '-' + PROJECTS, path.parent.name) is not None)
    for key in ('sourceCommit', 'sourceTree', 'runId', 'attempt'):
        require(type(data[key]) is str and data[key] == str(provenance[key]))
    require(re.fullmatch('[a-f0-9]{40}', data['sourceCommit']) is not None and re.fullmatch('[a-f0-9]{40}', data['sourceTree']) is not None)
    require(re.fullmatch('[0-9]{1,20}', data['runId']) is not None and re.fullmatch('[0-9]{1,20}', data['attempt']) is not None)
    for key in ('revoked', 'bodySettled', 'hookStarted', 'incomplete'):
        require(type(data[key]) is bool)
    require(not data['hookStarted'] or data['revoked'])
    require(type(data['coverage']) is dict and set(data['coverage']) == STATES[data['scenario']])
    require(all(type(v) is str and v in {'pending', 'started', 'complete', 'incomplete', 'not-required'} for v in data['coverage'].values()))
    require(type(data['errors']) is list and len(data['errors']) <= 6)
    require(all(type(e) is str and e in {'cancelled', 'body-failed', 'hook-failed', 'no-quiescence', 'receipt-failed', 'coverage-incomplete'} for e in data['errors']))
    require(len(data['errors']) == len(set(data['errors'])))
    if data['errors'] or not data['bodySettled'] or any(v not in {'complete', 'not-required'} for v in data['coverage'].values()):
        require(data['incomplete'])
    require(type(data['frames']) is list and len(data['frames']) <= 512)
    names = set()
    for frame in data['frames']:
        require(type(frame) is dict and set(frame) == {'file', 'sha256', 'bytes'})
        name = frame['file']
        require(type(name) is str and FRAME.fullmatch(name) is not None and name not in names)
        state = re.sub(r'-(?:[0-9]{3}|focus)\.png$', '', name.removeprefix('current-continuous-')) if name.startswith('current-continuous-') else (
            name.removesuffix('-post-assert.png') if name.startswith('workspace-') else
            re.sub(r'-(?:top|middle|footer)\.png$', '', name.removeprefix('current-scrollport-')))
        if name in {'current-scrollport-top.png', 'current-scrollport-middle.png', 'current-scrollport-footer.png'}:
            state = 'current'
        require(state in STATES[data['scenario']])
        names.add(name)
        require(type(frame['sha256']) is str and re.fullmatch('[a-f0-9]{64}', frame['sha256']) is not None)
        require(type(frame['bytes']) is int and 0 < frame['bytes'] <= 32 * 1024 * 1024)
        target = path.parent / name
        require(not target.is_symlink() and target.is_file() and target.stat().st_size == frame['bytes'])
        require(hashlib.sha256(target.read_bytes()).hexdigest() == frame['sha256'])
    return data
