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
import json
from pydo import Client

REQUIRED_ENV_VARS = ["DO_API_TOKEN"]


def _load_dotenv_fallback() -> None:
    """Load a local .env without python-dotenv.

    This avoids a subtle import-shadowing issue in this repo where python-dotenv's
    dependency chain imports `logging`, and an internal module name can be picked
    up instead of the stdlib module depending on sys.path.
    """
    try:
        from pathlib import Path

        # Candidate locations (prefer CWD for CLI usage; fall back to repo root).
        candidates = [Path.cwd() / ".env"]
        # .../digital_ocean/scripts/python/validate_dns.py -> repo root is 4 levels up
        candidates.append(Path(__file__).resolve().parents[4] / ".env")

        env_path = next((p for p in candidates if p.is_file()), None)
        if not env_path:
            return

        for raw_line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("\r")
            if not key:
                continue
            # Do not override already-set environment variables.
            os.environ.setdefault(key, value)
    except Exception:
        # Best-effort only; validation will fail later if required vars are missing.
        return

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
            print(f"  - {rec['type']} {rec['name']} -> {rec.get('data','')} [OK]")
    if not found:
        print(f"  [MISSING] No matching record found for type={record_type or 'ANY'}, name={name or 'ANY'}")

def main():
    _load_dotenv_fallback()
    parser = argparse.ArgumentParser(description="Validate Digital Ocean DNS records for a domain.")
    parser.add_argument('--domain', help='Domain to check (default: all domains in account or DO_APP_DOMAIN)')
    parser.add_argument('--record-type', help='DNS record type to check (A, CNAME, MX, etc.)')
    parser.add_argument('--name', help='Record name to check (e.g., @, www, mail)')
    parser.add_argument('--check-required', action='store_true', help='Check required app records (@, www, traefik, pgadmin, django-admin, flower)')
    parser.add_argument('--json', action='store_true', help='Emit records as JSON (machine-readable; no human formatting)')
    args = parser.parse_args()

    # Always load .env for DO_API_TOKEN
    validate_env()
    client = get_client()

    # If --domain is given, only check that domain; otherwise, list all
    if args.domain:
        domains = [args.domain]
    else:
        # Prefer DO_DOMAIN from env for project-specific checks when --check-required
        env_domain = os.getenv('DO_DOMAIN')
        domains = [env_domain] if env_domain else get_domains(client)

    if not domains:
        print("No domains found in your Digital Ocean account.")
        sys.exit(0)

    STANDARD_TYPES = ["A", "AAAA", "CNAME", "MX", "TXT", "NS", "SOA", "SRV", "CAA", "PTR"]
    for domain in domains:
        try:
            records = get_records(client, domain)
            if args.json:
                # Machine-readable output for scripts/tests (ASCII-safe).
                filtered = []
                for rec in records:
                    if args.record_type and rec.get('type') != args.record_type:
                        continue
                    if args.name and rec.get('name') != args.name:
                        continue
                    filtered.append({
                        'id': rec.get('id'),
                        'type': rec.get('type'),
                        'name': rec.get('name'),
                        'data': rec.get('data'),
                        'ttl': rec.get('ttl'),
                        'priority': rec.get('priority'),
                        'port': rec.get('port'),
                        'weight': rec.get('weight'),
                        'flags': rec.get('flags'),
                        'tag': rec.get('tag'),
                    })
                payload = {
                    'domain': domain,
                    'records': filtered,
                }
                sys.stdout.write(json.dumps(payload, ensure_ascii=True))
                sys.stdout.write('\n')
                continue

            if args.check_required:
                traefik_label = os.getenv('TRAEFIK_DNS_LABEL', 'traefik')
                pgadmin_label = os.getenv('PGADMIN_DNS_LABEL', 'pgadmin')
                admin_label = os.getenv('DJANGO_ADMIN_DNS_LABEL', 'admin')
                flower_label = os.getenv('FLOWER_DNS_LABEL', 'flower')
                swagger_label = os.getenv('SWAGGER_DNS_LABEL', 'swagger')
                required = ['@', 'www', traefik_label, pgadmin_label, admin_label, flower_label, swagger_label]
                print(f"\n[Required record presence checks]")
                for name in required:
                    has_a = any(r['type']=='A' and r['name']==name for r in records)
                    has_aaaa = any(r['type']=='AAAA' and r['name']==name for r in records)
                    a_status = '[OK]' if has_a else '[MISSING]'
                    aaaa_status = '[OK]' if has_aaaa else '-'
                    print(f"  - {name}: A {a_status}, AAAA {aaaa_status}")
            elif args.record_type or args.name:
                print_record_status(domain, records, args.record_type, args.name)
            else:
                print(f"\nDomain: {domain}")
                # Print all records
                for rec in records:
                    print(f"  - {rec['type']} {rec['name']} -> {rec.get('data','')}")
                # Check for all standard record types
                for rtype in STANDARD_TYPES:
                    found = any(rec['type'] == rtype for rec in records)
                    if found:
                        print(f"  [OK] At least one {rtype} record present.")
                    else:
                        print(f"  [MISSING] No {rtype} record found!")
        except Exception as e:
            print(f"  [ERROR] Error fetching records for {domain}: {e}", file=sys.stderr)
            continue

if __name__ == "__main__":
    main()
