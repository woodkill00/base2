from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class SearchSeoContractTests(unittest.TestCase):
    def test_search_query_is_tenant_public_fresh_and_tombstone_safe(self):
        source = (ROOT / 'api/repositories/site_content.py').read_text(encoding='utf-8')
        for marker in (
            "d.site_id=%s",
            "d.visibility='public'",
            'd.tombstoned_at IS NULL',
            "c.state='published'",
            'c.search_visible=TRUE',
            'source_updated_at',
        ):
            self.assertIn(marker, source)

    def test_build_and_runtime_metadata_are_manifest_driven(self):
        vite = (ROOT / 'react-app/vite.config.mjs').read_text(encoding='utf-8')
        for marker in ('robots.txt', 'sitemap.xml', 'application/ld+json', 'profile.seo.indexing'):
            self.assertIn(marker, vite)
        runtime = (ROOT / 'react-app/src/components/public/PageMetadata.jsx').read_text(encoding='utf-8')
        for marker in ('rel="canonical"', "property: 'og:title'", 'application/ld+json'):
            self.assertIn(marker, runtime)


if __name__ == '__main__':
    unittest.main()
