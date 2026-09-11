import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = fileURLToPath(new URL('../../../', import.meta.url));
const digest = (bytes) => createHash('sha256').update(bytes).digest('hex');
function source() {
  const files = execFileSync(
    'git',
    ['ls-files', '-z', '--cached', '--others', '--exclude-standard'],
    { cwd: root }
  )
    .toString()
    .split('\0')
    .filter(Boolean);
  return digest(
    Buffer.from(
      [...new Set(files)]
        .sort()
        .map((file) => {
          try {
            return `${file}\0${digest(readFileSync(path.join(root, file)))}`;
          } catch (error) {
            if (error.code === 'ENOENT') return `${file}\0DELETED`;
            throw error;
          }
        })
        .join('\n')
    )
  );
}
export default class EvidenceReporter {
  onBegin() {
    this.initial = source();
    this.commit = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root }).toString().trim();
    this.cases = [];
  }
  onTestEnd(test, result) {
    this.cases.push({
      title: test.titlePath(),
      status: result.status,
      attachments: result.attachments.map((item) => ({
        name: item.name,
        sha256: digest(item.body || readFileSync(item.path)),
        contentType: item.contentType,
      })),
    });
  }
  onEnd(result) {
    const stable = this.initial === source();
    const directory = path.join(root, '.artifacts/layout-109', process.env.LAYOUT_ATTEMPT);
    mkdirSync(directory, { recursive: true, mode: 0o700 });
    writeFileSync(
      path.join(directory, 'evidence.json'),
      JSON.stringify(
        {
          schemaVersion: 1,
          sourceCommit: this.commit,
          sourceDigest: this.initial,
          stableSource: stable,
          status: stable ? result.status : 'failed',
          node: process.version,
          platform: `${process.platform}/${process.arch}`,
          sharedLayout: !process.env.BASE2_LAYOUT_BASELINE,
          cases: this.cases,
        },
        null,
        2
      ),
      { flag: 'wx', mode: 0o600 }
    );
    if (!stable) return { status: 'failed' };
  }
}
