"""
validate_dns.py: Digital Ocean DNS Record Validator
Checks DNS records for configured domains and reports missing or misconfigured records.

Usage:
    python validate_dns.py --domain <domain> [--record-type <A|CNAME|MX|TXT|...>] [--name <record_name>]
    python validate_dns.py [--help|-h]

- If no domain is specified, uses DO_APP_DOMAIN or all domains from your account.
- If no record type is specified, checks all records for the domain.
- Requires .env with DO_API_TOKEN and (optionally) DO_APP_DOMAIN.
"""


import os
import sys
import argparse
from dotenv import load_dotenv
load_dotenv()
from pydo import Client

REQUIRED_ENV_VARS = ["DO_API_TOKEN"]

def validate_env():
    missing = [v for v in REQUIRED_ENV_VARS if not os.getenv(v)]
    if missing:
        print(f"Missing environment variables: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

def get_client():
    token = os.getenv("DO_API_TOKEN")
    return Client(token=token)

def get_domains(client):
    resp = client.domains.list()
    return [d['name'] for d in resp.get('domains', [])]

def get_records(client, domain):
    # Use the correct PyDo method for listing DNS records
    resp = client.domains.list_records(domain)
    return resp.get('domain_records', [])

def print_record_status(domain, records, record_type=None, name=None):
    print(f"\nDomain: {domain}")
    found = False
    for rec in records:
        if (not record_type or rec['type'] == record_type) and (not name or rec['name'] == name):
            found = True
            print(f"  - {rec['type']} {rec['name']} → {rec.get('data','')} ✔")
    if not found:
        print(f"  ✗ No matching record found for type={record_type or 'ANY'}, name={name or 'ANY'}")

def main():
    parser = argparse.ArgumentParser(description="Validate Digital Ocean DNS records for a domain.")
    parser.add_argument('--domain', help='Domain to check (default: all domains in account or DO_APP_DOMAIN)')
    parser.add_argument('--record-type', help='DNS record type to check (A, CNAME, MX, etc.)')
    parser.add_argument('--name', help='Record name to check (e.g., @, www, mail)')
    args = parser.parse_args()

    # Always load .env for DO_API_TOKEN
    validate_env()
    client = get_client()

    # If --domain is given, only check that domain; otherwise, list all
    if args.domain:
        domains = [args.domain]
    else:
        domains = get_domains(client)

    if not domains:
        print("No domains found in your Digital Ocean account.")
        sys.exit(0)

    STANDARD_TYPES = ["A", "AAAA", "CNAME", "MX", "TXT", "NS", "SOA", "SRV", "CAA", "PTR"]
    for domain in domains:
        try:
            records = get_records(client, domain)
            if args.record_type or args.name:
                print_record_status(domain, records, args.record_type, args.name)
            else:
                print(f"\nDomain: {domain}")
                # Print all records
                for rec in records:
                    print(f"  - {rec['type']} {rec['name']} → {rec.get('data','')}")
                # Check for all standard record types
                for rtype in STANDARD_TYPES:
                    found = any(rec['type'] == rtype for rec in records)
                    if found:
                        print(f"  ✔ At least one {rtype} record present.")
                    else:
                        print(f"  ✗ No {rtype} record found!")
        except Exception as e:
            print(f"  ✗ Error fetching records for {domain}: {e}", file=sys.stderr)
            continue

if __name__ == "__main__":
    main()
