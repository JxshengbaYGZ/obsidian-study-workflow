import importlib.util
from pathlib import Path
import unittest

path=Path(__file__).parents[1]/'skills/study-knowledge-base/scripts/ledger_check.py'
spec=importlib.util.spec_from_file_location('ledger_review',path)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class FinalReviewTests(unittest.TestCase):
    def test_claim_needs_record_and_self_check_is_not_independent(self):
        item=dict(id='q',kind='question',source_kind='scan',status='verified',source_check='matched',semantic_check='passed',evidence=['q.md'],reason='checked',final_review='passed')
        data=dict(expected_ids=['q'],items=[item])
        self.assertTrue(module.validate(data)[0])
        item['final_review_record']=dict(reviewer='reviewer',mode='self_check',evidence='review.md',scope='q')
        self.assertTrue(module.validate(data)[0])
        item['final_review_record']['mode']='independent'
        self.assertFalse(module.validate(data)[0])
