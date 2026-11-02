"""Allowlisted synthetic workspace lease/partial-frame diagnostics; never acceptance."""
import hashlib
import json
import re

NAME = 'workspace-capture-ownership.json'
BUDGET = 131072
PROJECTS = r'(?:chromium-(?:compact|phone-dpr3|landscape-touch|tablet|desktop|ultrawide|large-text|400-zoom|light|high-contrast)|firefox-desktop|webkit-mobile)'
CASES = {'records-schema': 'workspace-release-workspac-92e7c-ponsive-and-visually-stable',
         'imports-exports': 'workspace-release-workspac-a27fb-ponsive-and-visually-stable',
         'corpus': 'workspace-release-workspac-d0657-ponsive-and-visually-stable',
         'selected': 'workspace-release-selected-9c572-aves-or-discards-explicitly',
         'confirmations': 'workspace-release-workspac-c3eae-ons-cancel-without-mutation',
         'vocabulary': 'workspace-release-synthet-'}
STATES = {'records-schema': {'workspace-records', 'workspace-schema', 'current'},
          'imports-exports': {'workspace-imports', 'workspace-exports', 'current'},
          'corpus': {'workspace-records', 'workspace-schema', 'workspace-imports', 'workspace-exports', 'current'},
          'selected': {'workspace-records-selected-edit', 'workspace-records-selected-saved', 'current'},
          'confirmations': {'workspace-confirm-submit-review', 'workspace-confirm-publish', 'workspace-confirm-delete', 'workspace-confirm-restore', 'current'},
         'vocabulary': set()}
FRAME = re.compile(r'(?:workspace-confirm-(?:submit-review|publish|delete|restore)-attempt|current-continuous-(?:current|workspace-(?:records|schema|imports|exports|records-selected-edit|records-selected-saved))-(?:[0-9]{3}|focus)|current-scrollport-(?:(?:workspace-(?:records|schema|imports|exports|records-selected-edit|records-selected-saved))-)?(?:top|middle|footer)|workspace-(?:records|schema|imports|exports|records-selected-edit|records-selected-saved)-post-assert)\.png')


TITLES = {
    'corpus': 'workspace release corpus is accessible, responsive, and visually stable',
    'records-schema': 'workspace records and schema are accessible, responsive, and visually stable',
    'imports-exports': 'workspace imports and exports are accessible, responsive, and visually stable',
    'selected': 'selected record editing stays contained and saves or discards explicitly',
    'confirmations': 'workspace workflow confirmations cancel without mutation',
}


def project_for_case(case):
    scenario = scenario_for_case(case)
    return case[len(CASES[scenario]) + 1:] if scenario else None


def scenario_for_case(case):
    return next((kind for kind, prefix in CASES.items()
                 if kind != 'vocabulary' and re.fullmatch(re.escape(prefix) + '-' + PROJECTS, case)), None)


def state_registered(case, state):
    return state in STATES.get(scenario_for_case(case), set())


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
    require(type(data['schemaVersion']) is int and data['schemaVersion'] in (1, 2))
    require(data['schemaVersion'] == 1 or data['scenario'] == 'confirmations')
    require(data['scope'] == 'synthetic-workspace-ownership')
    require(type(data['scenario']) is str and data['scenario'] in {'corpus', 'records-schema', 'imports-exports', 'selected', 'confirmations'})
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
            name.removesuffix('-attempt.png').removesuffix('-post-assert.png') if name.startswith('workspace-') else
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
    if data['scenario'] == 'confirmations':
        for state, status in data['coverage'].items():
            if state != 'current' and status == 'complete':
                require(state + '-attempt.png' in names)
    if data['schemaVersion'] == 2:
        from scripts.python import confirmation_evidence
        project = project_for_case(path.parent.name)
        if project in confirmation_evidence.PROJECTS:
            require(all(status != 'not-required' for status in data['coverage'].values()))
        expected = {f'workspace-confirm-{state}-capture.json' for state in confirmation_evidence.STATES}
        receipts = list(path.parent.glob('workspace-confirm-*-capture.json'))
        require(all(receipt.name in expected for receipt in receipts))
        bound = {}
        frame_map = {frame['file']: frame for frame in data['frames']}
        for receipt in receipts:
            require(not receipt.is_symlink() and receipt.is_file() and receipt.stat().st_size <= confirmation_evidence.BUDGET)
            endpoint = confirmation_evidence.validate(receipt.read_bytes(), receipt, provenance)
            state = 'workspace-confirm-' + endpoint['state']
            require(state not in bound)
            bound[state] = endpoint
            if endpoint['image'] is not None:
                image = endpoint['image']
                require(image['file'] in frame_map)
                require(all(image[k] == frame_map[image['file']][k] for k in ('file', 'bytes', 'sha256')))
        for state in STATES['confirmations'] - {'current'}:
            if state + '-attempt.png' in names or data['coverage'][state] == 'complete':
                require(state in bound)
            if data['coverage'][state] == 'complete':
                require(bound[state]['complete'])
        if project == 'chromium-compact' and data['coverage']['current'] == 'complete':
            from scripts.python import continuous_evidence
            current_path = path.parent / 'continuous-current.json'
            require(not current_path.is_symlink() and current_path.is_file() and current_path.stat().st_size <= continuous_evidence.BUDGET)
            current = continuous_evidence.validate(current_path.read_bytes(), current_path,
                provenance['sourceCommit'], provenance['sourceTree'], project=project,
                run=str(provenance['runId']), attempt=str(provenance['attempt']))
            require(current['complete'])
            for segment in current['segments']:
                require(segment['file'] in frame_map)
                require(all(segment[k] == frame_map[segment['file']][k] for k in ('file', 'bytes', 'sha256')))
    return data
