#!/usr/bin/env python3
"""Validate planning consistency, not application or visual correctness."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
FILES = ('spec.md', 'plan.md', 'tasks.md', 'research.md', 'data-model.md',
         'analysis.md', 'quickstart.md', 'traceability.md', 'contracts/layout-acceptance.md')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(root=ROOT):
    docs = {name: (root / name).read_text(encoding='utf-8') for name in FILES}
    requirements = re.findall(r'\*\*(FR-\d{3})\*\*', docs['spec.md'])
    require(requirements == [f'FR-{i:03}' for i in range(1, 15)], 'requirement sequence')
    tasks = re.findall(r'^- \[([ x])\] (T\d{3}) \[([^\]]+)\] \(depends: ([^)]+)\) (.+)$',
                       docs['tasks.md'], re.M)
    require([t[1] for t in tasks] == [f'T{i:03}' for i in range(1, 29)], 'task sequence')
    seen, coverage = set(), {ref: set() for ref in requirements}
    for state, tid, refs, deps, text in tasks:
        require(state == ' ', 'planning tasks cannot claim completion')
        for dep in deps.split():
            require(dep == 'none' or dep in seen, f'{tid}: invalid predecessor')
        require(bool(refs.split()), f'{tid}: missing references')
        for ref in refs.split():
            require(ref in coverage, f'{tid}: unknown requirement')
            coverage[ref].add(tid)
        require(len(text) > 80 and '`' in text or len(text) > 130, f'{tid}: insufficient detail')
        seen.add(tid)
    for ref, tids in coverage.items():
        require(bool(tids), f'{ref}: uncovered')
        row = re.search(r'^\|\s*' + ref + r'\s*\|\s*(.+?)\s*\|$', docs['traceability.md'], re.M)
        require(row is not None and {v.strip() for v in row[1].split(',')} == tids,
                f'{ref}: traceability mismatch')
    for cycle in (1, 2, 3):
        require(f'Cycle {cycle}' in docs['analysis.md'], 'analysis cycle absent')
    require('run_complete_gate.py' in docs['plan.md'], 'release authority missing')
    require('owner approval' in docs['tasks.md'], 'owner checkpoint missing')
    for text in docs.values():
        require('NEEDS CLARIFICATION' not in text and '$ARGUMENTS' not in text, 'template placeholder')
    return {'requirements': len(requirements), 'tasks': len(tasks),
            'analysisCycles': len(re.findall(r'^## Cycle \d+', docs['analysis.md'], re.M)),
            'implementation': 'in_progress' if (root / 'progress.md').exists() else 'pending'}


if __name__ == '__main__':
    print(validate())
