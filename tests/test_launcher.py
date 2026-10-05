import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from run import verified_wheels


class BundledDependencyIntegrity(unittest.TestCase):
    def test_tampered_bundled_dependency_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            file = root/'dependency.whl'
            file.write_bytes(b'test artifact')
            manifest = {file.name: hashlib.sha256(file.read_bytes()).hexdigest()}
            (root/'SHA256SUMS.json').write_text(json.dumps(manifest))
            self.assertEqual(verified_wheels(root), root)
            file.write_bytes(b'tampered artifact')
            with self.assertRaises(SystemExit):
                verified_wheels(root)

    def test_missing_integrity_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(SystemExit):
                verified_wheels(Path(directory))
