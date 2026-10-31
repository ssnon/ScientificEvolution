#!/usr/bin/env python3
"""Reproduce V1.1's receipt-after-fit regression without any API or Journal writes."""
import copy
import unittest
import memory_bridge as mm
import science_frontier as sf

class ReceiptBudgetRegression(unittest.TestCase):
    def test_receipt_is_reserved_before_trim_and_full_p0_preserved(self):
        # Under V1.1 the view fits 86k before the receipt; the receipt itself
        # pushes the payload over 86k and the run stops mid-generation.
        payload={'program':{'problem':'P'*83000},
                 'problems':[{'id':'P0','parents':[],'question':'P0'}],
                 'prior_program_reviews':'R'*2400,
                 'active_scientific_work':[{'work_id':'W_ACTIVE','status':'ACTIVE'}]}
        original=copy.deepcopy(payload)
        original_hash=sf.sha(payload)
        self.assertLess(mm.jsize(payload),86000)
        # V1.2 shrinks repeat review prose to fund receipt headroom; no P0 or
        # active research contract data are removed.
        bounded=mm.bound_advisor_payload(payload,'OPP_D00099')
        self.assertLessEqual(mm.jsize(bounded),86000)
        self.assertEqual(bounded['program'],payload['program'])
        self.assertEqual([(r['id'],r['question'],r['parents']) for r in bounded['problems']],
                         [(r['id'],r['question'],r['parents']) for r in payload['problems']])
        self.assertEqual(bounded['active_scientific_work'],payload['active_scientific_work'])
        self.assertLess(mm.jsize(bounded['prior_program_reviews']),mm.jsize(payload['prior_program_reviews']))
        self.assertEqual(bounded['science_memory_request_receipt']['original_payload_sha256'],original_hash)
        self.assertEqual(bounded['science_memory_request_receipt']['model_attention_chars_before_receipt'],
                         mm.jsize({k:v for k,v in bounded.items() if k!='science_memory_request_receipt'}))
        self.assertEqual(payload,original)

    def test_receipt_budget_works_with_nondefault_limit(self):
        payload={'program':{'problem':'P'*1500},'prior_program_reviews':'R'*1700}
        bounded=mm.bound_advisor_payload(payload,'CTRL_D00099',max_chars=4200)
        self.assertLessEqual(mm.jsize(bounded),4200)
        self.assertEqual(bounded['program'],payload['program'])

    def test_uncompressible_science_fails_closed(self):
        payload={'program':{'problem':'P'*86000}}
        with self.assertRaisesRegex(RuntimeError,'MODEL_ATTENTION_BUDGET_UNSATISFIED_NO_SILENT_TRUNCATION'):
            mm.bound_advisor_payload(payload,'CTRL_D00100')

if __name__=='__main__':unittest.main(verbosity=2)
