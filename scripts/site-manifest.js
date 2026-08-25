#!/usr/bin/env node
'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

class ManifestError extends Error {}

const required = [
  'schemaVersion',
  'siteId',
  'slug',
  'name',
  'domains',
  'brand',
  'navigation',
  'seo',
  'legal',
  'locales',
  'defaultLocale',
  'consent',
  'analytics',
  'contact',
  'media',
  'search',
  'modules',
  'operationsProfile',
  'previewPolicy',
];
const allowed = new Set([...required, 'legalName']);
const hostPattern = /^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/;
const localePattern = /^[a-z]{2,3}(?:-[A-Z][a-z]{3})?(?:-(?:[A-Z]{2}|[0-9]{3}))?$/;
const secretKeyPattern = /password|secret|token|private.?key|api.?key|credential/i;
const secretValuePattern = /gh[pousr]_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{16,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|bearer\s+[A-Za-z0-9._~+/-]{12,}/i;

function rejectSecrets(value, location = 'manifest') {
  if (Array.isArray(value)) {
    value.forEach((entry, index) => rejectSecrets(entry, `${location}[${index}]`));
  } else if (value && typeof value === 'object') {
    Object.entries(value).forEach(([key, entry]) => {
      if (secretKeyPattern.test(key)) throw new ManifestError(`secret-bearing key at ${location}`);
      rejectSecrets(entry, `${location}.${key}`);
    });
  } else if (typeof value === 'string' && secretValuePattern.test(value)) {
    throw new ManifestError(`raw secret at ${location}`);
  }
}

function safePath(value, label) {
  if (
    typeof value !== 'string' ||
    !value.startsWith('/') ||
    value.startsWith('//') ||
    value.split('/').includes('..') ||
    /[?#\\\0]/.test(value)
  ) {
    throw new ManifestError(`${label} is not a safe local path`);
  }
}

function loadCatalog(repoRoot) {
  const payload = JSON.parse(
    fs.readFileSync(path.join(repoRoot, 'shared/config/module-catalog.json'), 'utf8'),
  );
  if (payload.schemaVersion !== 1 || !payload.modules) throw new ManifestError('invalid catalog');
  return payload.modules;
}

function validateManifest(payload, repoRoot = path.resolve(__dirname, '..')) {
  if (!payload || Array.isArray(payload) || typeof payload !== 'object') {
    throw new ManifestError('manifest must be an object');
  }
  const keys = Object.keys(payload);
  if (keys.some((key) => !allowed.has(key)) || required.some((key) => !(key in payload))) {
    throw new ManifestError('manifest fields differ');
  }
  rejectSecrets(payload);
  if (payload.schemaVersion !== 1) throw new ManifestError('schemaVersion must be 1');
  const domains = payload.domains;
  if (!Array.isArray(domains) || domains.length === 0) throw new ManifestError('domains required');
  const hosts = new Set();
  let canonical = 0;
  for (const domain of domains) {
    if (
      !domain ||
      Object.keys(domain).sort().join(',') !== 'host,kind' ||
      typeof domain.host !== 'string' ||
      domain.host !== domain.host.toLowerCase() ||
      !hostPattern.test(domain.host) ||
      hosts.has(domain.host) ||
      !['canonical', 'redirect', 'preview'].includes(domain.kind)
    ) {
      throw new ManifestError('domain contract is invalid');
    }
    hosts.add(domain.host);
    if (domain.kind === 'canonical') canonical += 1;
  }
  if (canonical !== 1) throw new ManifestError('exactly one canonical domain required');
  safePath(payload.brand?.logo, 'brand logo');
  const locales = payload.locales;
  if (
    !Array.isArray(locales) ||
    locales.length === 0 ||
    new Set(locales).size !== locales.length ||
    locales.some((locale) => typeof locale !== 'string' || !localePattern.test(locale)) ||
    !locales.includes(payload.defaultLocale)
  ) {
    throw new ManifestError('locale contract is invalid');
  }
  const catalog = loadCatalog(repoRoot);
  const installed = new Map();
  if (!Array.isArray(payload.modules)) throw new ManifestError('modules must be a list');
  for (const module of payload.modules) {
    if (
      !module ||
      typeof module.id !== 'string' ||
      installed.has(module.id) ||
      !catalog[module.id] ||
      !catalog[module.id].versions.includes(module.version) ||
      typeof module.enabled !== 'boolean'
    ) {
      throw new ManifestError('module compatibility failed');
    }
    installed.set(module.id, module);
  }
  for (const [id, module] of installed.entries()) {
    if (!module.enabled) continue;
    for (const dependency of catalog[id].requires) {
      if (!installed.get(dependency)?.enabled) throw new ManifestError(`module ${id} requires ${dependency}`);
    }
  }
  const paths = new Set();
  if (!Array.isArray(payload.navigation)) throw new ManifestError('navigation must be a list');
  for (const item of payload.navigation) {
    safePath(item?.path, 'navigation path');
    if (paths.has(item.path)) throw new ManifestError('duplicate navigation path');
    paths.add(item.path);
    if (item.module && !installed.get(item.module)?.enabled) {
      throw new ManifestError('navigation module is absent or disabled');
    }
  }
  Object.values(payload.legal).forEach((value) => safePath(value, 'legal path'));
  if (payload.search.enabled && !installed.get('search')?.enabled) {
    throw new ManifestError('search module is required');
  }
  if (payload.analytics.enabled !== (payload.analytics.provider === 'adapter')) {
    throw new ManifestError('analytics state disagrees');
  }
  if (payload.operationsProfile === 'preview' && payload.previewPolicy.idleAction !== 'destroy') {
    throw new ManifestError('preview must destroy idle resources');
  }
  return JSON.parse(JSON.stringify(payload));
}

function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stable(value[key])]));
  }
  return value;
}

function manifestDigest(payload, repoRoot) {
  const validated = validateManifest(payload, repoRoot);
  return crypto.createHash('sha256').update(JSON.stringify(stable(validated))).digest('hex');
}

function loadManifest(filename, repoRoot = path.resolve(__dirname, '..')) {
  if (fs.lstatSync(filename).isSymbolicLink()) throw new ManifestError('manifest must not be a symlink');
  const resolved = fs.realpathSync(filename);
  const stat = fs.statSync(resolved);
  if (!stat.isFile() || stat.size > 1_000_000 || (stat.mode & 0o002) !== 0) {
    throw new ManifestError('manifest file boundary failed');
  }
  return validateManifest(JSON.parse(fs.readFileSync(resolved, 'utf8')), repoRoot);
}

if (require.main === module) {
  try {
    const repoRoot = path.resolve(__dirname, '..');
    const payload = loadManifest(process.argv[2], repoRoot);
    process.stdout.write(
      `${JSON.stringify({ siteId: payload.siteId, digest: manifestDigest(payload, repoRoot) })}\n`,
    );
  } catch (error) {
    process.stderr.write(`site manifest rejected: ${error.message}\n`);
    process.exitCode = 2;
  }
}

module.exports = { ManifestError, loadManifest, manifestDigest, validateManifest };
