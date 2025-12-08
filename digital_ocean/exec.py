

"""
exec.py: Digital Ocean Exec Automation
Run commands in containers (Droplets or App Platform) using PyDo.

Usage:
	python exec.py --droplet <droplet_id|name> --cmd <command>
	python exec.py --app <app_id|name> --service <service_name> --cmd <command>
	python exec.py --help

Exits nonzero on error. Requires .env to be configured.
"""
import os
from dotenv import load_dotenv
load_dotenv()
import sys
import argparse

try:
	from pydo import Client
except ImportError:
	print("[ERROR] pydo not installed. Please run 'pip install pydo' in your environment.", file=sys.stderr)
	sys.exit(1)


# Import shared logging infrastructure
try:
	from .do_logging import get_logger, log_exec_start, log_exec_success, log_exec_error
except ImportError:
	from logging import getLogger as get_logger
	def log_exec_start(*a, **kw): pass
	def log_exec_success(*a, **kw): pass
	def log_exec_error(*a, **kw): pass

REQUIRED_ENV_VARS = ["DO_API_TOKEN"]
def validate_env():
	missing = [v for v in REQUIRED_ENV_VARS if not os.getenv(v)]
	if missing:
		print(f"Missing environment variables: {', '.join(missing)}", file=sys.stderr)
		sys.exit(1)

def get_client():
	token = os.getenv("DO_API_TOKEN")
	return Client(token=token)

def exec_on_droplet(client, droplet_id, command):
	# Digital Ocean does not support direct exec into droplets via API
	# This is a placeholder for SSH-based execution (user must have SSH key configured)
	log_exec_start(f"droplet:{droplet_id}", command)
	print(f"[INFO] Digital Ocean API does not support direct exec into droplets. Use SSH:")
	print(f"ssh root@<droplet_ip> '{command}'")
	log_exec_error(f"droplet:{droplet_id}", command, "API does not support exec; use SSH")
	return 127

def exec_on_app_service(client, app_id, service_name, command):
	# Digital Ocean App Platform supports command execution via API (limited)
	# This is a placeholder for the actual API call (PyDo may not support this directly)
	log_exec_start(f"app:{app_id}:{service_name}", command)
	print(f"[INFO] Digital Ocean App Platform exec is not yet supported via PyDo. Use 'doctl' CLI or dashboard.")
	log_exec_error(f"app:{app_id}:{service_name}", command, "API not supported; use doctl/dashboard")
	return 127

def main():
	parser = argparse.ArgumentParser(description="Run commands in Digital Ocean containers.")
	group = parser.add_mutually_exclusive_group(required=True)
	group.add_argument('--droplet', help='Droplet ID or name')
	group.add_argument('--app', help='App ID or name')
	parser.add_argument('--service', help='App Platform service name (required for --app)')
	parser.add_argument('--cmd', required=True, help='Command to run')
	args = parser.parse_args()

	validate_env()
	logger = get_logger()
	client = get_client()
	try:
		if args.droplet:
			rc = exec_on_droplet(client, args.droplet, args.cmd)
		elif args.app:
			if not args.service:
				print("[ERROR] --service is required when using --app", file=sys.stderr)
				sys.exit(2)
			rc = exec_on_app_service(client, args.app, args.service, args.cmd)
		else:
			print("[ERROR] Must specify either --droplet or --app", file=sys.stderr)
			sys.exit(2)
		log_exec_success(args.droplet or f"app:{args.app}:{args.service}", args.cmd, f"exit_code={rc}")
		sys.exit(rc)
	except Exception as e:
		log_exec_error(args.droplet or f"app:{args.app}:{args.service}", args.cmd, str(e))
		print(f"Error: {e}", file=sys.stderr)
		sys.exit(1)

if __name__ == "__main__":
	main()
