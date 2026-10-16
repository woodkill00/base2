"""Synthetic-only tests: never fetch real credentials."""
import copy
import unittest
from scripts.python.vault_google_credentials import read_google_credential, CredentialSelectionError

NAME = 'base2/GOOGLE_OAUTH_CLIENT_ID'
VALUE = 'synthetic-client.apps.googleusercontent.com'
HEADER = ('Managed by OpenClaw project-vault.\nproject_id=base2\nsecret_id=synthetic\n'
          'Never paste raw values into prompts, Discord, logs, screenshots, or tracked files.\n')


class CredentialTests(unittest.TestCase):
    def item(self):
        return {'name': NAME, 'type': 2, 'notes': HEADER + '${PLACEHOLDER}',
                'fields': [{'name': 'key', 'value': NAME.split('/')[1], 'type': 0},
                           {'name': 'value', 'value': VALUE, 'type': 1}]}

    def test_supported_sources(self):
        for source in ('custom', 'legacy', 'legacy-null-fields', 'both', 'no-notes', 'text'):
            with self.subTest(source=source):
                item = self.item()
                if source in ('legacy', 'legacy-null-fields', 'both'):
                    item['notes'] = HEADER + VALUE
                if source == 'legacy':
                    item['fields'] = []
                if source == 'legacy-null-fields':
                    item['fields'] = None
                if source == 'no-notes':
                    item['notes'] = None
                if source == 'text':
                    item['fields'][1]['type'] = 0
                self.assertEqual(read_google_credential(item, NAME), VALUE)

    def test_bad_inputs_fail_with_fixed_error(self):
        base = self.item()
        cases = [None, [], {**base, 'name': 'other'}, {**base, 'type': 1},
                 {**base, 'fields': 'bad'}, {**base, 'fields': [None]},
                 {**base, 'fields': {}}, {**base, 'notes': False},
                 {**base, 'notes': 12}, {**base, 'notes': 'unmanaged'},
                 {**base, 'notes': HEADER + 'other.apps.googleusercontent.com'},
                 {**base, 'fields': []}]
        for index in (0, 1):
            item = copy.deepcopy(base)
            item['fields'].append(copy.deepcopy(item['fields'][index]))
            cases.append(item)
        for value in (None, '', '${PLACEHOLDER}', 'bad', VALUE + '\nextra', 'x' * 5000):
            item = copy.deepcopy(base)
            item['fields'][1]['value'] = value
            cases.append(item)
        for kind in (True, 2, 3, None, '1'):
            item = copy.deepcopy(base)
            item['fields'][1]['type'] = kind
            cases.append(item)
        item = copy.deepcopy(base)
        item['fields'][0]['value'] = VALUE
        cases.append(item)
        for index, item in enumerate(cases):
            with self.subTest(case=index):
                with self.assertRaises(CredentialSelectionError) as error:
                    read_google_credential(item, NAME)
                self.assertEqual(str(error.exception), 'google-credential-invalid-or-ambiguous')

    def test_secret_and_scope(self):
        name = 'base2/GOOGLE_OAUTH_CLIENT_SECRET'
        item = {'name': name, 'type': 2, 'fields': [
            {'name': 'value', 'type': 1, 'value': 'GOCSPX-synthetic-only'}]}
        self.assertEqual(read_google_credential(item, name), 'GOCSPX-synthetic-only')
        with self.assertRaises(CredentialSelectionError):
            read_google_credential(item, 'base2/DIGITALOCEAN_TOKEN')
