

"""
info.py: Digital Ocean Info/Query Automation
Lists namespaces, domain names, and resource metadata using PyDo.

Usage:
	python info.py [--help|-h]

Exits nonzero on error. Requires .env to be configured.
"""
import os
from dotenv import load_dotenv
load_dotenv()
import sys
import logging
try:
	from pydo import Client
except ImportError:
	print("[ERROR] pydo not installed. Please run 'pip install pydo' in your environment.", file=sys.stderr)
	sys.exit(1)


# Import shared logging infrastructure
try:
	from .do_logging import get_logger, log_info_query_start, log_info_query_success, log_info_query_error
except ImportError:
	from logging import getLogger as get_logger
	def log_info_query_start(): pass
	def log_info_query_success(*a, **kw): pass
	def log_info_query_error(*a, **kw): pass

# Environment variable validation
REQUIRED_ENV_VARS = ["DO_API_TOKEN"]
def validate_env():
	missing = [v for v in REQUIRED_ENV_VARS if not os.getenv(v)]
	if missing:
		print(f"Missing environment variables: {', '.join(missing)}", file=sys.stderr)
		sys.exit(1)

def get_client():
	token = os.getenv("DO_API_TOKEN")
	return Client(token=token)

def list_namespaces(client):
	# Digital Ocean does not have explicit namespaces, but we can list projects
	projects = client.projects.list()
	return [p['name'] for p in projects.get('projects', [])]

def list_domains(client):
	domains = client.domains.list()
	return [d['name'] for d in domains.get('domains', [])]

def list_resource_metadata(client):
	droplets = client.droplets.list()
	apps = client.apps.list()
	volumes = client.volumes.list()
	return {
		"droplets": [d['name'] for d in droplets.get('droplets', [])],
		"apps": [a['spec']['name'] for a in apps.get('apps', []) if 'spec' in a and 'name' in a['spec']],
		"volumes": [v['name'] for v in volumes.get('volumes', [])]
	}

def main():
	if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
		print("Usage: python info.py [options]\nLists Digital Ocean namespaces, domain names, and resource metadata.")
		sys.exit(0)
	validate_env()
	logger = get_logger("digital_ocean.info")
	client = get_client()
	log_info_query_start()
	try:
		namespaces = list_namespaces(client)
		domains = list_domains(client)
		resources = list_resource_metadata(client)
		print("Namespaces:", namespaces)
		print("Domains:", domains)
		print("Resources:", resources)
		log_info_query_success(namespaces, domains, resources)
	except Exception as e:
		log_info_query_error(e)
		print(f"Error: {e}", file=sys.stderr)
		sys.exit(1)

if __name__ == "__main__":
	main()
