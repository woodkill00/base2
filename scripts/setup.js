'use strict';

const path = require('path');
const fs = require('fs');
const crypto = require('crypto');

const {
  fileExists,
  readText,
  parseEnv,
  applyToTemplate,
  backupFile,
  expandEnvContent,
  findUnresolvedPlaceholders,
} = require('./lib/envFile');
const { sanitizeProjectName, deriveIdentifiers } = require('./lib/derived');
const { detectPublicIpv4 } = require('./lib/ipDetect');
const { isPlaceholder } = require('./lib/placeholders');
const { validateEnv, CATEGORY } = require('./envRules');

function repoRoot() {
  return path.resolve(__dirname, '..');
}

function envPath(rootDir) {
  return path.join(rootDir, '.env');
}

function envBuildPath(rootDir) {
  return path.join(rootDir, '.env.build');
}

function envExamplePath(rootDir) {
  return path.join(rootDir, '.env.example');
}

function printChecklist({ envMap, stdout = console.log }) {
  const { required, missing, placeholders, invalid } = validateEnv(envMap);

  const byCategory = new Map();
  for (const c of required) byCategory.set(c, []);

  for (const item of [...missing, ...placeholders, ...invalid]) {
    const arr = byCategory.get(item.category) ?? [];
    arr.push(item);
    byCategory.set(item.category, arr);
  }

  stdout('');
  stdout('Next steps checklist (required categories):');

  const order = [
    CATEGORY.Core,
    CATEGORY.Secrets,
    CATEGORY.Admin,
    CATEGORY.Access,
    CATEGORY.TLS,
    CATEGORY.SMTP,
  ];
  for (const category of order) {
    if (!required.has(category)) continue;
    const issues = byCategory.get(category) ?? [];
    if (issues.length === 0) stdout(`- ${category}: OK`);
    else {
      stdout(`- ${category}: ${issues.length} item(s) to fix`);
      for (const it of issues) stdout(`  - ${it.key}: ${it.message}`);
    }
  }
}

/**
 * @param {{ rootDir?: string, prompt?: Function, stdout?: Function, stderr?: Function }} options
 */
async function runSetup(options = {}) {
  const rootDir = options.rootDir ?? repoRoot();
  if (process.stdin && process.stdin.isTTY === false) {
    throw new Error('Interactive prompt requires a TTY. Run from an interactive terminal.');
  }
  const prompt =
    options.prompt ??
    (() => {
      try {
        // Lazy-load so unit tests can run without installed deps.
        const inquirer = require('inquirer');
        const resolved =
          inquirer.prompt || (inquirer.default && inquirer.default.prompt) || inquirer.default;
        if (typeof resolved !== 'function') {
          throw new Error('inquirer prompt export not found');
        }
        return resolved;
      } catch (e) {
        const err = new Error('Missing dependency: inquirer. Run: npm install');
        err.cause = e;
        throw err;
      }
    })();
  const stdout = options.stdout ?? console.log;
  const stderr = options.stderr ?? console.error;

  const example = envExamplePath(rootDir);
  if (!fileExists(example)) {
    stderr('ERROR: .env.example is required but was not found.');
    process.exit(2);
  }

  const envBuildFile = envBuildPath(rootDir);
  const hasEnvBuild = fileExists(envBuildFile);

  if (hasEnvBuild) {
    stdout('==> .env.build already exists; asking whether to overwrite');
    const { overwrite } = await prompt([
      {
        type: 'confirm',
        name: 'overwrite',
        default: false,
        message: '.env.build already exists. Overwrite it (a timestamped backup will be created)?',
      },
    ]);
    if (!overwrite) {
      stdout('No changes made.');
      return { changed: false };
    }
    const backup = backupFile(envBuildFile, 'pre-setup');
    stdout(`Backup created: ${path.basename(backup)}`);
  }

  stdout('==> Gathering required settings for .env.build');
  const {
    projectName,
    websiteDomain,
    userMainEmail,
    applyEmailDefaults,
    userMainPassword,
    applyPasswordDefaults,
    userMainName,
    applyUserDefaults,
    env,
    deployMode,
    applyDevDefaults,
  } = await prompt([
    {
      type: 'input',
      name: 'projectName',
      message: 'Project name (lowercase letters, digits, hyphen):',
      validate: (v) => {
        try {
          sanitizeProjectName(v);
          return true;
        } catch (e) {
          return e.message;
        }
      },
    },
    {
      type: 'input',
      name: 'websiteDomain',
      message: 'Website domain (e.g. example.com):',
      validate: (v) => (String(v || '').trim() ? true : 'WEBSITE_DOMAIN is required'),
    },
    {
      type: 'input',
      name: 'userMainEmail',
      message: 'Primary email for certs/notifications (optional):',
      validate: (v) => {
        const value = String(v || '').trim();
        if (!value) return true;
        return value.includes('@') ? true : 'Enter a valid email address or leave blank.';
      },
    },
    {
      type: 'confirm',
      name: 'applyEmailDefaults',
      message: 'Apply primary email to all email fields by default?',
      default: true,
      when: (a) => String(a.userMainEmail || '').trim() !== '',
    },
    {
      type: 'password',
      name: 'userMainPassword',
      message: 'Primary user password (optional, leave blank to set later):',
      mask: '*',
    },
    {
      type: 'confirm',
      name: 'applyPasswordDefaults',
      message: 'Apply primary password to all default password fields?',
      default: false,
      when: (a) => String(a.userMainPassword || '').trim() !== '',
    },
    {
      type: 'input',
      name: 'userMainName',
      message: 'Primary username (optional, leave blank to set later):',
    },
    {
      type: 'confirm',
      name: 'applyUserDefaults',
      message: 'Apply primary username to all default username fields?',
      default: false,
      when: (a) => String(a.userMainName || '').trim() !== '',
    },
    {
      type: 'list',
      name: 'env',
      message: 'Environment:',
      choices: ['development', 'staging', 'production'],
      default: 'development',
    },
    {
      type: 'list',
      name: 'deployMode',
      message: 'Deploy mode:',
      choices: [
        { name: 'Local (Docker Compose)', value: 'local' },
        { name: 'DigitalOcean', value: 'digitalocean' },
      ],
      default: 'local',
    },
    {
      type: 'confirm',
      name: 'applyDevDefaults',
      message: 'Apply safe development defaults (development only)?',
      default: true,
      when: (a) => a.env === 'development',
    },
  ]);

  const templateContent = readText(example);
  const existingEnv = hasEnvBuild ? parseEnv(readText(envBuildFile)) : {};

  const allowedKeys = new Set([
    'PROJECT_NAME',
    'SITE_PROFILE',
    'WEBSITE_DOMAIN',
    'ENV',
    'DEPLOY_MODE',
    'APPLY_DEV_DEFAULTS',
    'USER_MAIN_EMAIL',
    'USER_MAIN_PASSWORD',
    'USER_MAIN_NAME',
    'APPLY_USER_NAME_DEFAULTS',
    'APPLY_USER_EMAIL_DEFAULTS',
    'APPLY_USER_PASSWORD_DEFAULTS',
    'TP_USER_IP_ADDRESS',
  ]);

  const base = {};
  for (const [key, value] of Object.entries(existingEnv)) {
    if (allowedKeys.has(key)) {
      base[key] = value;
    }
  }

  const emailValue = String(userMainEmail || '').trim();
  const passwordValue = String(userMainPassword || '').trim();
  const nameValue = String(userMainName || '').trim();

  const updates = {
    ...base,
    ...deriveIdentifiers({ projectName }),
    SITE_PROFILE: String(base.SITE_PROFILE || 'ember-studio'),
    WEBSITE_DOMAIN: websiteDomain.trim(),
    ENV: env,
    DEPLOY_MODE: deployMode,
    APPLY_DEV_DEFAULTS: applyDevDefaults ? 'true' : 'false',
  };

  if (typeof applyEmailDefaults === 'boolean') {
    updates.APPLY_USER_EMAIL_DEFAULTS = applyEmailDefaults ? 'true' : 'false';
  }

  if (emailValue) {
    updates.USER_MAIN_EMAIL = emailValue;
    if (applyEmailDefaults) {
      for (const key of [
        'DJANGO_SUPERUSER_EMAIL',
        'PGADMIN_DEFAULT_EMAIL',
        'TRAEFIK_CERT_EMAIL',
        'EMAIL_HOST_USER',
        'EMAIL_USER',
        'DEFAULT_FROM_EMAIL',
        'EMAIL_FROM',
        'SEED_ADMIN_EMAIL',
        'DO_ALERT_EMAIL',
      ]) {
        updates[key] = emailValue;
      }
    }
  }

  if (typeof applyPasswordDefaults === 'boolean') {
    updates.APPLY_USER_PASSWORD_DEFAULTS = applyPasswordDefaults ? 'true' : 'false';
  }

  if (passwordValue) {
    updates.USER_MAIN_PASSWORD = passwordValue;
  }

  if (typeof applyUserDefaults === 'boolean') {
    updates.APPLY_USER_NAME_DEFAULTS = applyUserDefaults ? 'true' : 'false';
  }

  if (nameValue) {
    updates.USER_MAIN_NAME = nameValue;
  }

  const tpSecretKeys = [
    'TP_DJANGO_SECRET_KEY',
    'TP_JWT_SECRET',
    'TP_TOKEN_PEPPER',
    'TP_IDENTITY_ENCRYPTION_KEY',
    'TP_CONTENT_WORKSPACE_STORAGE_KEY',
    'TP_OAUTH_STATE_SECRET',
    'TP_SEED_ADMIN_PASSWORD',
    'TP_SEED_DEMO_PASSWORD',
    'TP_DJANGO_SUPERUSER_PASSWORD',
    'TP_REDIS_PASSWORD',
    'TP_POSTGRES_PASSWORD',
    'TP_PGADMIN_PASSWORD',
    'TP_FLOWER_PASSWORD',
    'TP_TRAEFIK_PASSWORD',
    'TP_EMAIL_HOST_PASSWORD',
  ];

  const passwordDefaultsEnabled =
    String(applyPasswordDefaults || '')
      .trim()
      .toLowerCase() === 'true';
  const nameDefaultsEnabled =
    String(applyUserDefaults || '')
      .trim()
      .toLowerCase() === 'true';
  const passwordDefaultsKeys = new Set([
    'TP_SEED_ADMIN_PASSWORD',
    'TP_SEED_DEMO_PASSWORD',
    'TP_DJANGO_SUPERUSER_PASSWORD',
    'TP_REDIS_PASSWORD',
    'TP_POSTGRES_PASSWORD',
    'TP_PGADMIN_PASSWORD',
    'TP_FLOWER_PASSWORD',
    'TP_TRAEFIK_PASSWORD',
    'TP_EMAIL_HOST_PASSWORD',
  ]);

  for (const key of tpSecretKeys) {
    const current = existingEnv[key];
    if (!isPlaceholder(current, key)) {
      continue;
    }
    if (passwordDefaultsEnabled && passwordValue && passwordDefaultsKeys.has(key)) {
      updates[key] = passwordValue;
      continue;
    }
    updates[key] =
      key === 'TP_CONTENT_WORKSPACE_STORAGE_KEY'
        ? crypto.randomBytes(32).toString('base64url')
        : crypto.randomBytes(32).toString('hex');
  }

  const existingFlowerUser = existingEnv.TP_FLOWER_USERNAME;
  if (isPlaceholder(existingFlowerUser, 'TP_FLOWER_USERNAME') && nameDefaultsEnabled && nameValue) {
    updates.TP_FLOWER_USERNAME = nameValue;
  }

  const existingTraefikUser = existingEnv.TP_TRAEFIK_USERNAME;
  if (
    isPlaceholder(existingTraefikUser, 'TP_TRAEFIK_USERNAME') &&
    nameDefaultsEnabled &&
    nameValue
  ) {
    updates.TP_TRAEFIK_USERNAME = nameValue;
  }

  const existingIp = existingEnv.TP_USER_IP_ADDRESS;
  if (isPlaceholder(existingIp, 'TP_USER_IP_ADDRESS')) {
    try {
      const detected = await detectPublicIpv4();
      if (detected && detected.ip) {
        updates.TP_USER_IP_ADDRESS = detected.ip;
        stdout(`OK: Detected public IP ${detected.ip}`);
      }
    } catch (e) {
      stdout('WARN: Unable to detect public IP for TP_USER_IP_ADDRESS. Set it manually if needed.');
    }
  }

  const out = applyToTemplate(templateContent, updates);
  fs.writeFileSync(envBuildFile, out, 'utf8');

  const merged = parseEnv(out);

  stdout('OK: Wrote .env.build');
  printChecklist({ envMap: merged, stdout });

  stdout('');
  stdout('Recommended commands:');
  stdout('  - npm run setup:complete');
  stdout('  - node scripts/setup.js --render-env');
  stdout('  - npm run doctor');

  return { changed: true, envPath: envBuildFile };
}

/**
 * @param {{ rootDir?: string, stdout?: Function, stderr?: Function }} options
 */
async function renderFinalEnv(options = {}) {
  const rootDir = options.rootDir ?? repoRoot();
  const stdout = options.stdout ?? console.log;
  const stderr = options.stderr ?? console.error;

  const envBuildFile = envBuildPath(rootDir);
  if (!fileExists(envBuildFile)) {
    stderr('ERROR: .env.build is required but was not found. Run setup first.');
    process.exit(2);
  }

  const envFile = envPath(rootDir);
  if (fileExists(envFile)) {
    const backup = backupFile(envFile, 'pre-render');
    stdout(`Backup created: ${path.basename(backup)}`);
  }

  const buildContent = readText(envBuildFile);
  const envMap = parseEnv(buildContent);
  const expansionMap = { ...process.env, ...envMap };
  const expanded = expandEnvContent(buildContent, expansionMap);
  const unresolved = findUnresolvedPlaceholders(expanded);

  if (unresolved.length > 0) {
    stderr('ERROR: Unresolved placeholders remain in .env.build.');
    for (const item of unresolved) {
      stderr(`- ${item.key}: ${item.placeholders.join(', ')}`);
    }
    process.exit(2);
  }

  fs.writeFileSync(envFile, expanded, 'utf8');
  stdout('OK: Wrote .env from .env.build');
}

async function main() {
  const args = process.argv.slice(2);
  if (args.includes('--render-env')) {
    await renderFinalEnv();
    return;
  }
  await runSetup();
}

if (require.main === module) {
  main().catch((e) => {
    console.error('ERROR:', e && e.message ? e.message : e);
    process.exit(1);
  });
}

module.exports = { runSetup, renderFinalEnv };
