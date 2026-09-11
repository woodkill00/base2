"""Build propagation regression; no credentials or provider operations."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]

class DeploymentContract(unittest.TestCase):
    def test_shared_layout_is_enabled_in_both_supported_builds(self):
        for name in ('local.docker.yml', 'development.docker.yml'):
            self.assertIn('BASE2_SHARED_LAYOUT=${BASE2_SHARED_LAYOUT:-true}', (ROOT / name).read_text())
        docker = (ROOT / 'react-app/Dockerfile').read_text()
        self.assertIn('ARG BASE2_SHARED_LAYOUT=true', docker)
        self.assertLess(docker.index('ENV VITE_LAYOUT109_PREVIEW=${BASE2_SHARED_LAYOUT}'), docker.index('RUN npm run build'))
