"""Pure credential selection; no vault access, logging or provider authority."""
import re


class CredentialSelectionError(ValueError):
    """Safe fixed error code; never include supplied data."""


def read_google_credential(item, expected_name):
    patterns = {
        'base2/GOOGLE_OAUTH_CLIENT_ID': r'[A-Za-z0-9_-]+\.apps\.googleusercontent\.com',
        'base2/GOOGLE_OAUTH_CLIENT_SECRET': r'GOCSPX-[A-Za-z0-9_-]+',
    }

    def reject():
        raise CredentialSelectionError('google-credential-invalid-or-ambiguous')

    def candidate(value):
        if not isinstance(value, str):
            reject()
        value = value.strip()
        if not value or any(marker in value.lower() for marker in
                            ('your_', 'changeme', 'change_me', 'placeholder', '${')):
            return ''
        if len(value) > 4096 or not re.fullmatch(patterns[expected_name], value):
            reject()
        return value

    if (expected_name not in patterns or not isinstance(item, dict)
            or item.get('name') != expected_name or item.get('type') != 2):
        reject()
    fields = item.get('fields')
    if fields is None:
        fields = []
    if not isinstance(fields, list) or any(not isinstance(f, dict) for f in fields):
        reject()
    values = [f for f in fields if f.get('name') == 'value']
    keys = [f for f in fields if f.get('name') == 'key']
    if len(values) > 1 or len(keys) > 1:
        reject()
    if keys and keys[0].get('value') != expected_name.split('/')[1]:
        reject()
    custom = ''
    if values:
        if type(values[0].get('type')) is not int or values[0]['type'] not in (0, 1):
            reject()
        custom = candidate(values[0].get('value'))
    notes = item.get('notes')
    if notes is None:
        notes = ''
    if not isinstance(notes, str):
        reject()
    legacy = ''
    if notes:
        lines = notes.split('\n', 4)
        if (len(lines) != 5 or lines[0] != 'Managed by OpenClaw project-vault.'
                or lines[1] != 'project_id=base2' or not lines[2].startswith('secret_id=')
                or lines[3] != 'Never paste raw values into prompts, Discord, logs, screenshots, or tracked files.'):
            reject()
        legacy = candidate(lines[4])
    if custom and legacy and custom != legacy:
        reject()
    if not (custom or legacy):
        reject()
    return custom or legacy
