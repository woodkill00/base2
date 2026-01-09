/*
 Simple style guard for the glass feature.
 Flags global overrides and !important in glass styles.
*/
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const STYLES_DIR = path.join(ROOT, 'src', 'styles');
const COMPONENTS_DIR = path.join(ROOT, 'src', 'components', 'glass');
const ALLOWED_GLOBAL_FILE = path.join(STYLES_DIR, 'tokens.css');

function listCssFiles(dir) {
  const results = [];
  if (!fs.existsSync(dir)) return results;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...listCssFiles(full));
    } else if (entry.isFile() && entry.name.endsWith('.css')) {
      results.push(full);
    }
  }
  return results;
}

function checkFile(file) {
  const text = fs.readFileSync(file, 'utf8');
  const lines = text.split(/\r?\n/);
  const violations = [];
  const globalSelectorRegex = /^\s*(html|body|:root|\.dark)\s*\{/;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line.includes('!important')) {
      violations.push({ file, line: i + 1, reason: 'Avoid !important' });
    }
    if (globalSelectorRegex.test(line) && path.resolve(file) !== path.resolve(ALLOWED_GLOBAL_FILE)) {
      violations.push({ file, line: i + 1, reason: 'Global selector outside tokens.css' });
    }
  }
  return violations;
}

function main() {
  const files = [
    ...listCssFiles(STYLES_DIR),
    ...listCssFiles(COMPONENTS_DIR),
  ];
  let allViolations = [];
  for (const file of files) {
    allViolations = allViolations.concat(checkFile(file));
  }
  if (allViolations.length) {
    console.error('Style guard violations found:');
    for (const v of allViolations) {
      console.error(`${v.file}:${v.line} - ${v.reason}`);
    }
    process.exit(1);
  } else {
    console.log('Style guard passed: no global overrides or !important usage found.');
  }
}

if (require.main === module) {
  main();
}
