

#!/bin/bash
# info.sh: CLI wrapper for Digital Ocean info/query script
# Usage: ./info.sh [--help|-h]
# Lists namespaces, domain names, and resource metadata from Digital Ocean.
# Exits nonzero on error. Requires .env to be configured.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}/../.."
cd "$PROJECT_ROOT"

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
	echo "Usage: ./info.sh [options]"
	echo "Lists Digital Ocean namespaces, domain names, and resource metadata."
	exit 0
fi

# Activate Python venv if exists
if [ -f ".venv/bin/activate" ]; then
	source .venv/bin/activate
elif [ -f ".venv/Scripts/activate" ]; then
	source .venv/Scripts/activate
fi

python digital_ocean/info.py "$@"
