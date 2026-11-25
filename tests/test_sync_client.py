import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('sync_client', Path(__file__).resolve().parents[1] / 'sync-client.py')
sync_client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync_client)


class ClientUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source, self.target = self.root / 'installed', self.root / 'private'
        for root, executable in [(self.source, b'new'), (self.target, b'old')]:
            (root / 'win64').mkdir(parents=True)
            (root / 'win64/WorldOfTanks.exe').write_bytes(executable)
            (root / 'version.xml').write_text('<root><version>2.4.2.0</version></root>')
            (root / 'paths.xml').write_text('<root><Package>res/packages/current.pkg</Package><Path>./mods/2.4.2.0</Path></root>')
        (self.source / 'res/packages').mkdir(parents=True)
        (self.source / 'res/packages/current.pkg').write_bytes(b'resources')
        (self.target / 'res').symlink_to(self.source / 'res', target_is_directory=True)
        (self.target / 'data.wgpdc').write_bytes(b'obsolete')
        self.idle = patch.object(sync_client.subprocess, 'check_output', return_value='')
        self.idle.start()
        self.addCleanup(self.idle.stop)

    def test_refresh_and_backup(self):
        self.assertIn('win64/WorldOfTanks.exe', sync_client.check(self.source, self.target)[0])
        (self.source / 'mods/2.4.2.0').mkdir(parents=True)
        (self.source / 'mods/2.4.2.0/current.wotmod').write_bytes(b'mod')
        sync_client.sync(self.source, self.target, True)
        self.assertEqual(sync_client.check(self.source, self.target), ([], []))
        self.assertFalse((self.target / 'data.wgpdc').exists())
        self.assertEqual(next(self.root.glob('client-backup-*/data.wgpdc')).read_bytes(), b'obsolete')
        self.assertTrue((self.target / 'res').is_symlink())
        self.assertEqual((self.source / 'res/packages/current.pkg').read_bytes(), b'resources')
        self.assertEqual((self.target / 'mods/2.4.2.0/current.wotmod').read_bytes(), b'mod')

    def test_incomplete_install_refused(self):
        (self.source / 'res/packages/current.pkg').unlink()
        with self.assertRaisesRegex(ValueError, 'missing packages'):
            sync_client.check(self.source, self.target)
        self.assertEqual((self.target / 'win64/WorldOfTanks.exe').read_bytes(), b'old')

    def test_running_game_refused(self):
        with patch.object(sync_client.subprocess, 'check_output', return_value='C:\\Games\\WorldOfTanks.exe'):
            with self.assertRaisesRegex(ValueError, 'Close World of Tanks'):
                sync_client.sync(self.source, self.target, False)

    def test_failed_verification_restores_private_files(self):
        with patch.object(sync_client, 'check', side_effect=ValueError('post-copy failure')):
            with self.assertRaisesRegex(ValueError, 'post-copy failure'):
                sync_client.sync(self.source, self.target, False)
        self.assertEqual((self.target / 'win64/WorldOfTanks.exe').read_bytes(), b'old')
        self.assertEqual((self.target / 'data.wgpdc').read_bytes(), b'obsolete')


if __name__ == '__main__':
    unittest.main()
