from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = ROOT / "react-app" / "Dockerfile"
NGINX_MAIN = ROOT / "react-app" / "nginx" / "nginx.conf"
NGINX_SITE = ROOT / "react-app" / "nginx" / "default.conf"


def builder_findings(text: str, builder: str) -> list[str]:
    findings: list[str] = []
    if builder not in {"classic", "buildkit"}:
        return ["unknown builder"]
    if re.search(r"^RUN\s+cat\s+<<", text, flags=re.MULTILINE):
        findings.append(f"{builder} builder rejects generated heredoc configuration")
    if "COPY nginx/nginx.conf /etc/nginx/nginx.conf" not in text:
        findings.append("checked-in nginx main config is not copied")
    renderer = "RUN node scripts/google-nginx-policy.mjs nginx/default.conf /app/nginx-google.conf"
    copy = "COPY --from=build /app/nginx-google.conf /etc/nginx/conf.d/default.conf"
    if renderer not in text or copy not in text or text.index(renderer) > text.index(copy):
        findings.append("checked-in nginx site policy is not rendered and copied")
    return findings


class ReactImageBuildTests(unittest.TestCase):
    def test_missing_policy_render_or_copy_is_rejected(self):
        text = DOCKERFILE.read_text(encoding="utf-8")
        for removed in (
            'RUN node scripts/google-nginx-policy.mjs nginx/default.conf /app/nginx-google.conf',
            'COPY --from=build /app/nginx-google.conf /etc/nginx/conf.d/default.conf',
        ):
            self.assertTrue(builder_findings(text.replace(removed, ''), 'classic'))

    def test_supported_builders_use_portable_dockerfile(self):
        text = DOCKERFILE.read_text(encoding="utf-8")
        for builder in ("classic", "buildkit"):
            with self.subTest(builder=builder):
                self.assertEqual([], builder_findings(text, builder))

    def test_checked_in_nginx_contract(self):
        main = NGINX_MAIN.read_text(encoding="utf-8")
        site = NGINX_SITE.read_text(encoding="utf-8")
        self.assertIn("user nginx;", main)
        self.assertIn("include /etc/nginx/conf.d/*.conf;", main)
        self.assertIn("listen 8080;", site)
        self.assertIn("try_files $uri $uri/ /index.html;", site)
        self.assertIn("try_files $uri =404;", site)
        self.assertIn('default "no-store"', site)
        self.assertIn('"public, max-age=31536000, immutable"', site)
        self.assertIn('Cache-Control $base2_cache_control always', site)

    def test_spa_fallback_precedes_static_asset_404(self):
        site = NGINX_SITE.read_text(encoding="utf-8")
        fallback = site.index("try_files $uri $uri/ /index.html;")
        static_404 = site.index("try_files $uri =404;")
        self.assertLess(fallback, static_404)


if __name__ == "__main__":
    unittest.main()
