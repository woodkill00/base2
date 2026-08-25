'use strict';

const { spawnSync } = require('node:child_process');

function findPowerShell() {
  for (const candidate of ['pwsh', 'powershell']) {
    const result = spawnSync(candidate, ['-NoProfile', '-Command', '$PSVersionTable.PSVersion.ToString()'], {
      encoding: 'utf8',
    });
    if (result.status === 0) return candidate;
  }
  return null;
}

module.exports = { findPowerShell };
