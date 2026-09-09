import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_spec = importlib.util.spec_from_file_location(
    "sha256sums",
    Path(__file__).resolve().parents[2] / "scripts" / "sha256sums.py",
)
sums = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sums)


class Sha256SumsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dist = Path(self.tmp.name)
        self.patches = [
            patch.object(sums, "DIST", self.dist),
            patch.object(sums, "SUMS", self.dist / "SHA256SUMS"),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def test_write_then_verify_roundtrip(self):
        archive = self.dist / "EverythingMarkdown-0.0.0-dev-linux-x64.zip"
        archive.write_bytes(b"payload")
        self.assertEqual(0, sums.write())
        line = (self.dist / "SHA256SUMS").read_text(encoding="utf-8").strip()
        self.assertEqual(f"{hashlib.sha256(b'payload').hexdigest()}  {archive.name}", line)
        self.assertEqual(0, sums.verify())

    def test_verify_detects_tampering(self):
        archive = self.dist / "app-linux-x64.zip"
        archive.write_bytes(b"good")
        sums.write()
        archive.write_bytes(b"tampered")
        self.assertEqual(1, sums.verify())

    def test_write_without_archives_fails(self):
        self.assertEqual(1, sums.write())

    def test_verify_without_sums_file_fails(self):
        self.assertEqual(1, sums.verify())

    def test_verify_flags_unlisted_archive(self):
        (self.dist / "listed-linux-x64.zip").write_bytes(b"a")
        sums.write()
        (self.dist / "sneaked-windows-x64.zip").write_bytes(b"b")
        self.assertEqual(1, sums.verify())


if __name__ == "__main__":
    unittest.main()
