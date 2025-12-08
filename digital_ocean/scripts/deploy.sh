
#!/bin/bash
# Digital Ocean Deploy Script
# Usage: ./deploy.sh [--dry-run] [--help|-h]
# Deploys app to Digital Ocean using PyDo and environment variables.
#
# Exits nonzero on error. Requires .env to be configured.

set -e

if [[ "$1" == "--help" || "$1" == "-h" ]]; then
  echo "Usage: ./deploy.sh [--dry-run]"
  echo "Deploys app to Digital Ocean using PyDo."
  exit 0
fi

python ../deploy.py "$@"
