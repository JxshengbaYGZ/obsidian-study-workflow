import importlib.util
from pathlib import Path
import unittest

path=Path(__file__).resolve().parents[1]/'skills/study-knowledge-base/scripts/ledger_check.py'
spec=importlib.util.spec_from_file_location('ledger',path)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class LedgerTests(unittest.TestCase):
    def test_evidence_and_scope(self):
        base=dict(id='q',kind='question',source_kind='scan',status='verified',source_check='matched',semantic_check='passed',evidence=['source page 1; independently checked'],reason='checked')
        cases=[({},True,False),({'source_check':'unread'},True,True),({'evidence':[' ']},True,True),({'status':'pending'},True,True),({'status':'pending'},False,False),({'status':'duplicate'},False,True),({'status':'no_independent_tip'},False,True)]
        for changes,complete,rejected in cases:
            with self.subTest(changes=changes,complete=complete):
                errors,_=module.validate(dict(expected_ids=['q'],items=[dict(base,**changes)]),complete)
                self.assertEqual(bool(errors),rejected)
        errors,_=module.validate(dict(expected_ids=['q','missing'],items=[base]))
        self.assertTrue(errors)

if __name__=='__main__':
    unittest.main()
