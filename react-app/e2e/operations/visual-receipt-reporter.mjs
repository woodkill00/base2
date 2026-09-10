import { createHash } from 'node:crypto';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';

const output = resolve('../specs/106-production-readiness-program/operations-visual-runner.json');

export default class VisualReceiptReporter {
  constructor() {
    this.results = [];
  }

  onTestEnd(test, result) {
    const project = test.parent.project()?.name || 'unknown';
    const primary = test.title === 'operations center is accessible responsive and visually stable';
    const state = test.title.includes('truthful empty') ? 'empty-error' : 'recovery';
    const captures = result.attachments
      .filter((attachment) => attachment.name.startsWith('visual:') && attachment.body)
      .map((attachment) => ({
        name: attachment.name.slice('visual:'.length),
        sha256: createHash('sha256').update(attachment.body).digest('hex'),
      }))
      .sort((left, right) => left.name.localeCompare(right.name));
    this.results.push({
      project,
      title: test.title,
      status: result.status,
      assertionId: primary ? 'operations-primary' : `operations-${state}`,
      captures,
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
