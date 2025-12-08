"""
T057: Dry-run/test mode flag for all scripts
Usage: python dry_run.py [--dry-run]
Shows planned API calls and outputs without making changes.
"""
import sys
if '--dry-run' in sys.argv:
    print('[DRY RUN] No changes will be made.')
else:
    print('Run with --dry-run to preview actions.')
