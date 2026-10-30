import tempfile
import unittest
import zipfile
from pathlib import Path

from experiments.freshness.artifact_archives import valid_archive


class FreshnessArtifactArchiveTests(unittest.TestCase):
    def test_archive_requires_exact_file_count_and_valid_crc(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'artifact.zip'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('block/manifest.json', '{}')
                archive.writestr('block/schedule.json', '{}')
            self.assertTrue(valid_archive(path, 2))
            self.assertFalse(valid_archive(path, 3))


if __name__ == '__main__':
    unittest.main()
