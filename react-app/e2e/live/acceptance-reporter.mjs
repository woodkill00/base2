import { execFileSync } from 'node:child_process';
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';
import { evaluateAcceptance } from './acceptance-contract.mjs';

const root = fileURLToPath(new URL('../../../', import.meta.url));
const git = (args) => execFileSync('git', args, { cwd: root }).toString().trim();
export default class AcceptanceReporter {
  constructor(
    options = {},
    source = () => ({
      commit: git(['rev-parse', 'HEAD']),
      clean: git(['status', '--porcelain']) === '',
    })
  ) {
    this.source = source;
    this.environment = options.environment || process.env;
  }
  onBegin(config) {
    if (config.updateSnapshots !== 'none')
      throw new Error('Live acceptance forbids baseline updates');
    const source = this.source();
    this.commit = source.commit;
    this.clean = source.clean;
    this.cases = [];
  }
  onTestEnd(test, result) {
    this.cases.push({ title: test.title, status: result.status, retry: result.retry });
  }
  onEnd(result) {
    const source = this.source();
    const report = evaluateAcceptance({
      cases: this.cases,
      status: result.status,
      sourceCommit: this.commit,
      sourceClean: this.clean && source.clean,
      sourceStable:
        this.commit === source.commit && this.commit === this.environment.BASE2_LIVE_SOURCE_COMMIT,
    });
    report.runId = this.environment.BASE2_LIVE_RUN_ID;
    writeFileSync(
      join(this.environment.BASE2_LIVE_EVIDENCE_DIR, 'acceptance.json'),
      JSON.stringify(report, null, 2) + '\n',
      { flag: 'wx', mode: 0o600 }
    );
    if (report.status !== 'passed') return { status: 'failed' };
  }
}
