'use strict';

const { isPlaceholder } = require('./lib/placeholders');

const DEPLOY_MODES = /** @type {const} */ ({
  LOCAL: 'local',
  DIGITALOCEAN: 'digitalocean',
});

const ENVS = /** @type {const} */ ({
  DEVELOPMENT: 'development',
  STAGING: 'staging',
  PRODUCTION: 'production',
});

const CATEGORY = /** @type {const} */ ({
  Core: 'Core',
  Secrets: 'Secrets',
  Admin: 'Admin',
  Access: 'Access',
  TLS: 'TLS',
  SMTP: 'SMTP',
  OAuth: 'OAuth',
  Other: 'Other',
});

const CATEGORIES = {
  [CATEGORY.Core]: {
    requiredByDefault: true,
    keys: ['PROJECT_NAME', 'ENV', 'WEBSITE_DOMAIN', 'DEPLOY_MODE', 'APPLY_DEV_DEFAULTS'],
  },
  [CATEGORY.Secrets]: {
    requiredByDefault: true,
    keys: [
      'DJANGO_SECRET_KEY',
      'REDIS_PASSWORD',
      'JWT_SECRET',
      'TOKEN_PEPPER',
      'OAUTH_STATE_SECRET',
    ],
  },
  [CATEGORY.Admin]: {
    requiredByDefault: true,
    keys: [
      'DJANGO_SUPERUSER_NAME',
      'DJANGO_SUPERUSER_PASSWORD',
      'DJANGO_SUPERUSER_EMAIL',
      'SEED_ADMIN_EMAIL',
      'SEED_ADMIN_PASSWORD',
    ],
  },
  [CATEGORY.Access]: {
    requiredByDefault: true,
    keys: [
      'TRAEFIK_DASH_BASIC_USERS',
      'FLOWER_BASIC_USERS',
      'DJANGO_ADMIN_ALLOWLIST',
      'FLOWER_ALLOWLIST',
      'PGADMIN_ALLOWLIST',
    ],
  },
  [CATEGORY.TLS]: {
    requiredByDefault: false,
    keys: ['TRAEFIK_CERT_EMAIL', 'TRAEFIK_CERT_RESOLVER'],
  },
  [CATEGORY.SMTP]: {
    requiredByDefault: false,
    keys: [
      'EMAIL_HOST',
      'EMAIL_PORT',
      'EMAIL_HOST_USER',
      'EMAIL_HOST_PASSWORD',
      'DEFAULT_FROM_EMAIL',
    ],
  },
  [CATEGORY.OAuth]: {
    requiredByDefault: false,
    keys: ['GOOGLE_OAUTH_CLIENT_ID', 'GOOGLE_OAUTH_CLIENT_SECRET', 'GOOGLE_OAUTH_REDIRECT_URI'],
  },
};

function normalizeDeployMode(value) {
  if (!value) return 'unknown';
  const v = String(value).trim().toLowerCase();
  if (v === DEPLOY_MODES.LOCAL) return DEPLOY_MODES.LOCAL;
  if (v === DEPLOY_MODES.DIGITALOCEAN || v === 'digital_ocean' || v === 'do')
    return DEPLOY_MODES.DIGITALOCEAN;
  return 'unknown';
}

function normalizeEnv(value) {
  if (!value) return 'unknown';
  const v = String(value).trim().toLowerCase();
  if (v === ENVS.DEVELOPMENT) return ENVS.DEVELOPMENT;
  if (v === ENVS.STAGING) return ENVS.STAGING;
  if (v === ENVS.PRODUCTION) return ENVS.PRODUCTION;
  return 'unknown';
}

function requiredCategories({ env, deployMode }) {
  const normalizedEnv = normalizeEnv(env);
  const normalizedDeployMode = normalizeDeployMode(deployMode);
  const required = new Set([CATEGORY.Core, CATEGORY.Secrets, CATEGORY.Admin, CATEGORY.Access]);

  const needsTls =
    normalizedEnv === ENVS.PRODUCTION || normalizedDeployMode === DEPLOY_MODES.DIGITALOCEAN;
  const needsSmtp =
    normalizedEnv === ENVS.PRODUCTION || normalizedDeployMode === DEPLOY_MODES.DIGITALOCEAN;

  if (needsTls) {
    required.add(CATEGORY.TLS);
  }
  if (needsSmtp) {
    required.add(CATEGORY.SMTP);
  }

  return required;
}

function findCategoryForKey(key) {
  for (const [categoryName, category] of Object.entries(CATEGORIES)) {
    if (category.keys.includes(key)) return categoryName;
  }
  return CATEGORY.Other;
}

/**
 * @param {Record<string, string | undefined>} envMap
 * @param {{ env?: string, deployMode?: string }} options
 */
function validateEnv(envMap, options = {}) {
  const required = requiredCategories({
    env: options.env ?? envMap.ENV,
    deployMode: options.deployMode ?? envMap.DEPLOY_MODE,
  });

  /** @type {Array<{category: string, key: string, message: string, required: boolean}>} */
  const missing = [];
  /** @type {Array<{category: string, key: string, message: string, required: boolean}>} */
  const placeholders = [];
  /** @type {Array<{category: string, key: string, message: string, required: boolean}>} */
  const invalid = [];

  for (const categoryName of Object.keys(CATEGORIES)) {
    const category = CATEGORIES[categoryName];
    const isCategoryRequired = required.has(categoryName);

    for (const key of category.keys) {
      const value = envMap[key];
      const isRequired = isCategoryRequired;

      if (isRequired && (value === undefined || String(value).trim() === '')) {
        missing.push({
          category: categoryName,
          key,
          message: `${key} is missing`,
          required: true,
        });
        continue;
      }

      if (isRequired && isPlaceholder(value, key)) {
        const tpMatch = typeof value === 'string' ? value.match(/^\$\{(TP_[A-Z0-9_]+)\}$/) : null;
        if (tpMatch) {
          const tpKey = tpMatch[1];
          const tpValue = envMap[tpKey];
          if (tpValue && !isPlaceholder(tpValue, tpKey)) {
            continue;
          }
        }
        placeholders.push({
          category: categoryName,
          key,
          message: `${key} is still a placeholder`,
          required: true,
        });
      }
    }
  }

  // Cross-field validation
  const projectName = envMap.PROJECT_NAME;
  if (projectName && !/^[a-z0-9-]+$/.test(projectName)) {
    invalid.push({
      category: findCategoryForKey('PROJECT_NAME'),
      key: 'PROJECT_NAME',
      message: 'PROJECT_NAME must match /^[a-z0-9-]+$/',
      required: required.has(findCategoryForKey('PROJECT_NAME')),
    });
  }

  return { required, missing, placeholders, invalid };
}

module.exports = {
  DEPLOY_MODES,
  ENVS,
  CATEGORY,
  CATEGORIES,
  normalizeDeployMode,
  normalizeEnv,
  requiredCategories,
  validateEnv,
  isPlaceholder,
};
