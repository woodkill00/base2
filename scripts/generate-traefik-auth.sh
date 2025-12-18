#!/usr/bin/env bash
# Generate a Traefik Basic-Auth htpasswd entry locally without Docker/openssl.
# Uses Node.js bcrypt for strong hashes. Outputs both raw and .env-safe lines.

set -euo pipefail

USERNAME=${1:-}
PASSWORD=${2:-}
ALGO=${3:-apr1} # apr1|bcrypt

if [[ -z "$USERNAME" || -z "$PASSWORD" ]]; then
  echo "Usage: ./scripts/generate-traefik-auth.sh <username> <password>" >&2
  exit 1
fi

# Basic validation: no spaces/colon in username
if [[ "$USERNAME" =~ [[:space:]] || "$USERNAME" =~ : ]]; then
  echo "ERROR: Username must not contain spaces or colons" >&2
  exit 2
fi

# Require node
if ! command -v node >/dev/null 2>&1; then
  echo "ERROR: Node.js is required. Please install Node and retry." >&2
  exit 3
fi

NODE_SCRIPT_FILE=$(mktemp 2>/dev/null || echo "/tmp/node_htpasswd_$$.js")
cat >"$NODE_SCRIPT_FILE" <<'JS'
const crypto = require('crypto');

function to64(value, length) {
  const itoa64 = './0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz';
  let out = '';
  while (--length >= 0) {
    out += itoa64[value & 0x3f];
    value >>= 6;
  }
  return out;
}

function apr1(pass, salt) {
  // Implementation of Apache MD5 (apr1) based on reference algorithm.
  const magic = '$apr1$';
  salt = salt.replace(/\$/g, '').slice(0, 8);

  let ctx = crypto.createHash('md5');
  ctx.update(pass + magic + salt);

  let alt = crypto.createHash('md5');
  alt.update(pass + salt + pass);
  let altResult = alt.digest();

  for (let i = pass.length; i > 0; i -= 16) {
    ctx.update(altResult.slice(0, Math.min(16, i)));
  }

  for (let i = pass.length; i > 0; i >>= 1) {
    if (i & 1) ctx.update(Buffer.from([0]));
    else ctx.update(Buffer.from(pass[0]));
  }

  let result = ctx.digest();

  for (let i = 0; i < 1000; i++) {
    let ctxi = crypto.createHash('md5');
    if (i % 2) ctxi.update(pass);
    else ctxi.update(result);
    if (i % 3) ctxi.update(salt);
    if (i % 7) ctxi.update(pass);
    if (i % 2) ctxi.update(result);
    else ctxi.update(pass);
    result = ctxi.digest();
  }

  const r = result;
  const v = [
    (r[0] << 16) | (r[6] << 8) | r[12],
    (r[1] << 16) | (r[7] << 8) | r[13],
    (r[2] << 16) | (r[8] << 8) | r[14],
    (r[3] << 16) | (r[9] << 8) | r[15],
    (r[4] << 16) | (r[10] << 8) | r[5],
    r[11]
  ];

  let out = '';
  out += to64(v[0], 4);
  out += to64(v[1], 4);
  out += to64(v[2], 4);
  out += to64(v[3], 4);
  out += to64(v[4], 4);
  out += to64(v[5], 2);

  return `${magic}${salt}$${out}`;
}

const user = process.argv[2];
const pass = process.argv[3];
const algo = process.argv[4] || 'apr1';

if (algo === 'apr1') {
  const salt = crypto.randomBytes(6).toString('base64').replace(/[^A-Za-z0-9]/g, '').slice(0, 8);
  const digest = apr1(pass, salt);
  console.log(`${user}:${digest}`);
} else if (algo === 'bcrypt') {
  let bcrypt;
  try { bcrypt = require('bcrypt'); }
  catch (e) {
    console.error('bcrypt module not found. Install with: npm i -g bcrypt');
    process.exit(1);
  }
  bcrypt.hash(pass, 10).then(h => {
    console.log(`${user}:${h}`);
  }).catch(e => { console.error(e); process.exit(1); });
}
JS

RAW=$(node "$NODE_SCRIPT_FILE" "$USERNAME" "$PASSWORD" "$ALGO")

if [[ -z "$RAW" ]]; then
  echo "ERROR: Empty output from bcrypt generation" >&2
  exit 4
fi

# Safety checks: only allow [A-Za-z0-9./$] and no whitespace
HASH=${RAW#*:}
if [[ "$HASH" =~ [[:space:]] ]]; then
  echo "ERROR: Hash contains whitespace; aborting" >&2
  exit 5
fi
if ! [[ "$HASH" =~ ^[A-Za-z0-9./$]+$ ]]; then
  echo "ERROR: Hash contains unsafe characters; aborting" >&2
  exit 6
fi
if [[ "$ALGO" == "bcrypt" ]]; then
  if ! [[ "$HASH" =~ \$2[aby]\$ ]]; then
    echo "ERROR: Expected bcrypt marker (\$2a/\$2b/\$2y); aborting" >&2
    exit 7
  fi
else
  if ! [[ "$HASH" =~ \$apr1\$ ]]; then
    echo "ERROR: Expected apr1 marker (\$apr1\$); aborting" >&2
    exit 7
  fi
fi

# Escape $ to $$ for .env safety
ENV_SAFE=${RAW//\$/\$\$}

echo
echo "Raw htpasswd:"
echo "  $RAW"
echo
echo ".env-safe line:"
echo "  TRAEFIK_DASH_BASIC_USERS=$ENV_SAFE"
echo
echo "Copy the .env-safe line into your .env and redeploy Traefik."
