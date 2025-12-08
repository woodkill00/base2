

#!/bin/bash
# exec.sh: CLI wrapper for Digital Ocean exec script
# Usage: ./exec.sh --droplet <id|name> --cmd <command>
#        ./exec.sh --app <id|name> --service <service> --cmd <command>
# Runs commands in containers on Digital Ocean.
# Exits nonzero on error. Requires .env to be configured.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}/../.."
cd "$PROJECT_ROOT"

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
	echo "Usage: ./exec.sh --droplet <id|name> --cmd <command>"
	echo "       ./exec.sh --app <id|name> --service <service> --cmd <command>"
	echo "Runs a command in a Digital Ocean droplet or app service."
	exit 0
fi

# Activate Python venv if exists
if [ -f ".venv/bin/activate" ]; then
	source .venv/bin/activate
elif [ -f ".venv/Scripts/activate" ]; then
	source .venv/Scripts/activate
fi

python digital_ocean/exec.py "$@"
