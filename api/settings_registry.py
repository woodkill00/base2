"""Closed, safe discovery metadata; never an authorization or activation mechanism.

Module enablement comes from the generated runtime manifest. An enabled module is
not evidence that its roadmap engine or external provider has been implemented.
"""
from __future__ import annotations

from api.security.identity import is_allowed


PERSONAL_CATEGORIES = (
    'overview', 'profile', 'security', 'privacy', 'notifications', 'appearance', 'language-region',
)


def _control(key, label, category, anchor, description, synonyms, *, risk='reversible'):
    return {
        'id': key, 'label': label, 'category': category, 'anchor': anchor,
        'description': description, 'synonyms': synonyms,
        'scope': 'account' if category == 'profile' else 'personal',
        'permission': 'authenticated', 'availability': 'available',
        'audit_action': 'user.preferences_updated' if key.startswith('preferences.') else
                        'user.notification_preferences_updated' if category == 'notifications' else None,
        'risk': risk, 'path': f'/settings/{category}#{anchor}',
    }


CONTROLS = (
    _control('profile.display_name', 'Display name', 'profile', 'display-name',
             'The name shown on your profile.', 'name identity public'),
    _control('profile.avatar_url', 'Avatar image', 'profile', 'avatar-url',
             'A public HTTPS profile image; local or credential-bearing URLs are rejected.',
             'photo picture avatar'),
    _control('profile.bio', 'Profile bio', 'profile', 'bio',
             'Your public profile description.', 'about biography'),
    _control('preferences.theme', 'Color theme', 'appearance', 'theme',
             'Choose light, dark, or your system color scheme.', 'night mode dark light'),
    _control('preferences.contrast', 'Contrast', 'appearance', 'contrast',
             'Choose standard, high, or system contrast.', 'readability accessibility'),
    _control('preferences.motion', 'Motion', 'appearance', 'motion',
             'Choose full, reduced, or system motion.', 'animation movement accessibility'),
    _control('preferences.density', 'Density', 'appearance', 'density',
             'Choose comfortable or compact spacing.', 'spacing compact comfortable'),
    _control('preferences.locale', 'Language', 'language-region', 'locale',
             'Choose a language supported by this site.', 'translation locale'),
    _control('preferences.timezone', 'Time zone', 'language-region', 'timezone',
             'Save your preferred IANA time zone.', 'timezone clock region'),
    _control('preferences.week_start', 'Week starts on', 'language-region', 'week-start',
             'Save your preferred first day of the week.', 'calendar monday sunday saturday'),
    *(_control(f'notifications.{family}.email', f'{label} email', 'notifications',
               f'notification-{family}-email',
               'Stored delivery preference. Delivery-engine integration is not yet available.',
               f'{family} alerts email digest messages')
      for family, label in (('security', 'Security'), ('transactional', 'Transactional'),
                            ('product', 'Product'), ('marketing', 'Marketing'))),
    _control('privacy.deactivation', 'Deactivate account', 'privacy', 'deactivate-confirmation',
             'Suspend account access through the existing verified privacy workflow.',
             'pause suspend deactivate', risk='sensitive'),
    _control('privacy.deletion', 'Delete account data', 'privacy', 'delete-confirmation',
             'Start the separate, confirmed account-deletion workflow.',
             'erase remove privacy data delete', risk='destructive'),
)


def _module(key, label, description, *, workspace=None):
    return {'id': key, 'label': label, 'description': description, 'workspace': workspace}


MODULES = (
    _module('content-workspace', 'Content workspace',
            'Manage existing collections, records, schemas and publication workflows.',
            workspace=('/workspace', 'content-workspace.read', 'Open content workspace')),
    _module('media', 'Media library',
            'Manage existing media assets and their supported policies.',
            workspace=('/media', 'media.read', 'Open media library')),
    _module('content', 'Site content', 'Content foundation; module activation is deployment-managed.'),
    _module('blog', 'Blog & publishing', 'Publishing content foundation; editorial policy settings are planned.'),
    _module('portfolio', 'Portfolio', 'Portfolio content foundation; domain-specific settings are planned.'),
    _module('gallery', 'Gallery', 'Gallery content foundation; domain-specific settings are planned.'),
    _module('documentation', 'Documentation', 'Documentation content foundation; domain-specific settings are planned.'),
    _module('catalog', 'Catalog', 'Catalog content foundation; commerce policy settings are planned.'),
    _module('commerce', 'Storefront & commerce',
            'Limited provider contract: no live payments, tax, shipping or returns settings.'),
    _module('marketplace', 'Marketplace', 'Module foundation; seller, payout and dispute engines are planned.'),
    _module('listing', 'Listings', 'Listing content foundation; seller and listing-policy settings are planned.'),
    _module('community', 'Community & social',
            'Pre-moderated submission foundation; social graph and moderation policy settings are planned.'),
    _module('events', 'Events', 'Event inventory foundation; event-policy settings are planned.'),
    _module('booking', 'Bookings',
            'Reservation foundation; availability, cancellation and calendar settings are planned.'),
    _module('support', 'Support & CRM',
            'Content/module foundation, not a complete CRM or support automation engine.'),
    _module('forms', 'Forms & lead capture', 'Forms foundation; routing and consent-policy settings are planned.'),
    _module('membership', 'Membership', 'Module foundation; entitlement policy settings are planned.'),
    _module('subscription', 'Subscriptions', 'Module foundation; live billing and seat-policy settings are planned.'),
)


def discovery(*, manifest: dict, role: str | None, accounts_enabled: bool) -> dict:
    categories = [
        {'id': key, 'path': '/settings' if key == 'overview' else f'/settings/{key}',
         'version': 'v1', 'scope': 'account' if key in {'profile', 'security'} else 'personal'}
        for key in PERSONAL_CATEGORIES
    ]
    if accounts_enabled and is_allowed(role or '', 'audit.read'):
        categories.append({'id': 'organization', 'path': '/settings/organization',
                           'version': 'v1', 'scope': 'organization'})
        if is_allowed(role or '', 'credential.create'):
            categories.append({'id': 'developer', 'path': '/settings/developer',
                               'version': 'v1', 'scope': 'organization'})
    categories.append({'id': 'site-capabilities', 'path': '/settings/site-capabilities',
                       'version': 'v1', 'scope': 'site'})
    enabled = {item['id'] for item in manifest.get('modules', []) if item.get('enabled') is True}
    modules = []
    for definition in MODULES:
        key = definition['id']
        workspace = definition['workspace']
        action = None
        if key in enabled and accounts_enabled and workspace and is_allowed(role or '', workspace[1]):
            action = {'path': workspace[0], 'label': workspace[2]}
        modules.append({
            'id': key, 'label': definition['label'], 'description': definition['description'],
            'scope': 'site', 'enabled': key in enabled, 'managed_by': 'deployment',
            'state': 'available' if action else 'limited' if key in enabled else 'disabled',
            'action': action,
        })
    return {'schema_version': 1, 'categories': categories, 'controls': list(CONTROLS),
            'modules': modules, 'locales': manifest.get('locales', ['en'])}
