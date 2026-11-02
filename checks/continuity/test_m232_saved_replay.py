"""Integration regression against actual DurableModel in the host repository.

Fake provider: no OpenRouter requests or expenses. Verifies saved-call reuse,
ledger settlement, and fail-closed uncertainty preservation.
"""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from e2core.core import EvolutionJournal, EvidenceError
from e2core.provider import DurableModel
from e2core.m232_budget import budget_report


class SavedModelReplayTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.exp=Path(self.tmp.name)/'exp'; self.exp.mkdir()
        (self.exp/'autonomous.json').write_text('{}')
        (self.exp/'M232_DEV_BUDGET.json').write_text(json.dumps({
            'protocol':'M232_DEVELOPMENT_BUDGET_V1','limit_usd':1.0,
            'model_rates_per_million_usd':{'m232-test-model':{'input':1,'output':2}},
            'reserve_multiplier':1.25
        }))
        self.j=EvolutionJournal(self.exp/'CYCLE_000/SYN_01')
        self.j.init('A unit-test scientific problem')
        self.env=patch.dict(os.environ,{'M232_BUDGET_REQUIRED':'YES','FAKG_RESEARCH_ALLOW_PAID':'YES'})
        self.env.start()

    def tearDown(self):
        self.env.stop();self.tmp.cleanup()

    def test_reuse_saved_ident_no_second_provider_call(self):
        calls=[]
        def fake_provider(wire,timeout):
            calls.append(wire)
            return json.dumps({'choices':[{'message':{'content':'{"example":"saved"}'},
                                           'finish_reason':'stop'}],
                               'usage':{'cost':0.005,'prompt_tokens':10,'completion_tokens':10}}).encode()
        first=DurableModel(self.j,provider=fake_provider,approved=True,max_new_calls=1,
                           model='m232-test-model',max_tokens=100,mode='EXTERNAL')
        out=first.call('PMI_UNIT','CONTROLLER',None,'system',{'problem':'A'})
        self.assertEqual(json.loads(out)['example'],'saved')
        self.assertEqual(len(calls),1)
        self.assertEqual(self.j.verify().model_calls['PMI_UNIT']['state'],'SAVED')
        second=DurableModel(self.j,provider=lambda *_args,**_kw: self.fail('provider must not run'),
                            approved=False,max_new_calls=0,model='m232-test-model',max_tokens=100,
                            mode='EXTERNAL')
        self.assertEqual(second.call('PMI_UNIT','CONTROLLER',None,'system',{'problem':'A'}),out)
        self.assertEqual(len(calls),1)
        self.assertEqual(budget_report(self.exp)['states']['SAVED']['count'],1)

    def test_unknown_provider_outcome_no_automatic_retry(self):
        def broken(wire,timeout):
            raise OSError('synthetic network failure')
        first=DurableModel(self.j,provider=broken,approved=True,max_new_calls=1,
                           model='m232-test-model',max_tokens=100,mode='EXTERNAL')
        with self.assertRaisesRegex(EvidenceError,'PROVIDER_UNKNOWN_OUTCOME_NO_AUTOMATIC_RETRY'):
            first.call('PMI_UNCERTAIN','CONTROLLER',None,'system',{'problem':'B'})
        self.assertEqual(self.j.verify().model_calls['PMI_UNCERTAIN']['state'],'UNCERTAIN')
        self.assertEqual(budget_report(self.exp)['states']['RESERVED']['count'],1)
        second=DurableModel(self.j,provider=lambda *_a,**_kw: self.fail('no re-billing'),
                            approved=True,max_new_calls=1,model='m232-test-model',max_tokens=100,
                            mode='EXTERNAL')
        with self.assertRaisesRegex(EvidenceError,'UNCERTAIN_MODEL_CALL_NO_AUTOMATIC_RETRY'):
            second.call('PMI_UNCERTAIN','CONTROLLER',None,'system',{'problem':'B'})

if __name__=='__main__':unittest.main()
