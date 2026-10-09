"""检查独立安装、来源处置门禁和自编电路小样。"""
from pathlib import Path
import cmath
import math
import re
import shutil
import tempfile
import unittest
from test_ledger import module

ROOT = Path(__file__).resolve().parents[1]


class PortableTests(unittest.TestCase):
    def test_skill_links_survive_standalone_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            skill = Path(directory) / 'skill'
            shutil.copytree(ROOT / 'skills/study-knowledge-base', skill)
            for file in skill.rglob('*.md'):
                for target in re.findall(r'\]\(([^)]+)\)', file.read_text(encoding='utf-8')):
                    if '://' in target:
                        continue
                    target_path = (file.parent / target.split('#')[0]).resolve()
                    self.assertTrue(target_path.is_relative_to(skill.resolve()), str(file))
                    self.assertTrue(target_path.is_file(), target)

    def test_unread_cannot_be_disposed_as_duplicate_or_no_tip(self):
        for status in ['duplicate', 'no_independent_tip']:
            item = dict(id='a', kind='tip', source_kind='transcript', status=status,
                        source_check='unread', semantic_check='unread', evidence=[],
                        reason='试图绕过未读检查', duplicate_of='existing')
            errors, _ = module.validate(dict(expected_ids=['a'], existing_ids=['existing'], items=[item]), True)
            self.assertTrue(errors)

    def test_duplicate_cycle_is_rejected(self):
        items = [dict(id=a,kind='tip',source_kind='transcript',status='duplicate',source_check='matched',
                      semantic_check='passed',evidence=['读过'],reason='重复',duplicate_of=b)
                 for a,b in [('a','b'),('b','a')]]
        errors,_ = module.validate(dict(expected_ids=['a','b'],items=items),True)
        self.assertTrue(errors)

    def test_rc_example_by_impedance(self):
        resistance, capacitance = 1000, 100e-9
        omega = 1 / (resistance * capacitance)
        impedance = 1 / (1j * omega * capacitance)
        transfer = impedance / (resistance + impedance)
        self.assertAlmostEqual(omega / (2 * math.pi),1591.5494309189535)
        self.assertAlmostEqual(abs(transfer),1/math.sqrt(2))
        self.assertAlmostEqual(cmath.phase(transfer),-math.pi/4)


if __name__ == '__main__':
    unittest.main()
