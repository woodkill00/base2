
"""
Environment Variable Validation for Digital Ocean Integration
Checks required variables and prints clear error messages if missing.

Usage:
    python env_check.py [--help|-h]

Exits nonzero on error. Requires .env to be configured.
"""
import os
import sys

REQUIRED_VARS = [
    "DO_API_TOKEN",
    "DO_API_REGION",
    "DO_API_IMAGE",
    "DO_APP_NAME"
]

OPTIONAL_VARS = [
    "DO_API_SIZE", "DO_REGISTRY_NAME", "DO_APP_SPEC_PATH", "DO_BACKUPS_ENABLED",
    "DO_IPV6_ENABLED", "DO_USER_DATA_PATH", "DO_DROPLET_NAME", "DO_DROPLET_SIZE",
    "DO_DROPLET_IMAGE", "DO_DROPLET_COUNT", "DO_DROPLET_PRIVATE_NETWORKING",
    "DO_DROPLET_VOLUME_ID", "DO_REPOSITORY_NAME", "DO_IMAGE_TAG", "DO_SPACES_KEY",
    "DO_SPACES_SECRET", "DO_SPACES_REGION", "DO_OAUTH_CLIENT_ID", "DO_OAUTH_CLIENT_SECRET",
    "DO_DEPLOY_TIMEOUT", "DO_TEARDOWN_TIMEOUT", "DO_LOG_LEVEL", "DO_API_RETRY_LIMIT",
    "DO_API_RETRY_DELAY", "DO_APP_ENV_EXAMPLE", "DO_PROJECT_ID", "DO_FIREWALL_ID",
    "DO_VPC_UUID", "DO_TAGS", "DO_MONITORING_ENABLED", "DO_ALERT_EMAIL", "DO_APP_DOMAIN",
    "DO_APP_BRANCH", "DO_APP_REPO_URL", "DO_APP_AUTOSCALE", "DO_APP_MIN_INSTANCES",
    "DO_APP_MAX_INSTANCES", "DO_API_TIMEOUT", "DO_API_BASE_URL", "DO_APP_HEALTHCHECK_PATH",
    "DO_APP_HEALTHCHECK_INTERVAL", "DO_APP_HEALTHCHECK_TIMEOUT", "DO_APP_HEALTHCHECK_THRESHOLD"
]


def check_required_env_vars():
    """
    Checks required environment variables and exits if any are missing.
    Used for both CLI and test validation.
    """
    missing = [var for var in REQUIRED_VARS if not os.getenv(var)]
    if missing:
        print(f"ERROR: Missing required environment variables: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)
    # Optionally warn about unset optional variables
    unset_optional = [var for var in OPTIONAL_VARS if not os.getenv(var)]
    if unset_optional:
        print(f"[WARN] Unset optional variables: {', '.join(unset_optional)}")
    print("All required Digital Ocean environment variables are set.")

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
        print("Usage: python env_check.py [options]\nChecks required Digital Ocean environment variables.")
        sys.exit(0)
    try:
        check_required_env_vars()
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()
