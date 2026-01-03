const { spawnSync } = require('child_process');

function hasPatchPackage() {
  try {
    require.resolve('patch-package');
    return true;
  } catch (e) {
    return false;
  }
}

if (!hasPatchPackage()) {
  console.log('patch-package not installed (likely --omit=dev). Skipping patches.');
  process.exit(0);
}

const result = spawnSync('npx', ['patch-package'], { stdio: 'inherit', shell: true });
process.exit(result.status ?? 0);
