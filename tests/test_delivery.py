import importlib.util
from pathlib import Path
import tempfile
import unittest

path=Path(__file__).parents[1]/'skills/study-knowledge-base/scripts/check_delivery.py'
spec=importlib.util.spec_from_file_location('delivery',path)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class DeliveryTests(unittest.TestCase):
    def test_markdown_image_is_checked_without_manifest_entry(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'note.md').write_text('![原图](crop.png)',encoding='utf-8')
            self.assertTrue(module.check(root,['note.md'])['errors'])
            (root/'crop.png').write_bytes(b'image')
            self.assertFalse(module.check(root,['note.md'])['errors'])
    def test_missing_empty_and_present_attachment(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'note.md').write_text('![[crop.png]]',encoding='utf-8')
            self.assertTrue(module.check(root,['note.md'])['errors'])
            (root/'crop.png').touch()
            self.assertTrue(module.check(root,['note.md'])['errors'])
            (root/'crop.png').write_bytes(b'image')
            self.assertFalse(module.check(root,['note.md'])['errors'])
    def test_ambiguous_and_outside(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name in ('a','b'):
                (root/name).mkdir()
                (root/name/'target.md').write_text('content',encoding='utf-8')
            (root/'note.md').write_text('[[target]]',encoding='utf-8')
            self.assertTrue(module.check(root,['note.md','../outside.md'])['errors'])
