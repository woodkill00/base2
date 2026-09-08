import { createHash } from 'node:crypto';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';

const output = resolve('../specs/106-production-readiness-program/operations-visual-runner.json');

export default class VisualReceiptReporter {
  constructor() {
    this.results = [];
  }

  onTestEnd(test, result) {
    this.results.push({
      project: test.parent.project()?.name || 'unknown',
      title: test.title,
      status: result.status,
    });
  }

  onEnd(result) {
    const tests = this.results.sort((left, right) =>
      `${left.project}:${left.title}`.localeCompare(`${right.project}:${right.title}`)
    );
    const body = { schemaVersion: 1, status: result.status, tests };
    body.digest = createHash('sha256').update(JSON.stringify(body)).digest('hex');
    mkdirSync(dirname(output), { recursive: true });
    writeFileSync(output, `${JSON.stringify(body, null, 2)}\n`, { mode: 0o600 });
  }
}
