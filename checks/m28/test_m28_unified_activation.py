"""M28 unified M25 activation contract: real new ROOT, fake provider only.

NO paid provider; this fixture deliberately uses synthetic rates and must NEVER
be copied as an actual experiment budget or treated as a billing guarantee.
"""
import contextlib
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

import meta_research_autonomy as meta
from e2core.activation_contract import (PROTOCOL as PROFILE_PROTOCOL, DEFAULTS,
                                        check_m28_experiment, enforce_m28_provider_activation)
from e2core.core import EvolutionJournal
from e2core.provider import DurableModel

MODEL = 'openai/gpt-5.6-luna'

class TestM28UnifiedActivation(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.tmpdir=Path(self.tmp.name)
        self.saved_env={k:os.environ.get(k) for k in [*DEFAULTS,'FAKG_RESEARCH_ALLOW_PAID']}
        self.addCleanup(self._restore)
        for k in DEFAULTS:
            os.environ.pop(k,None)
        os.environ['M232_BUDGET_REQUIRED']='YES'
        os.environ.pop('FAKG_RESEARCH_ALLOW_PAID',None)
        self.exp=self.tmpdir/'A41'
        self.problem=self.tmpdir/'P0.txt'
        self.problem.write_text('Finite conditional inference P0',encoding='utf8')
        self.profile_path=self.tmpdir/'activation.json'
        self.budget_path=self.tmpdir/'budget.json'
        self.features={**DEFAULTS,'M232_BUDGET_REQUIRED':'YES'}
        self.profile_path.write_text(json.dumps({'protocol':PROFILE_PROTOCOL,
            'model':MODEL,'purpose':'no-paid integration contract test',
            'features':self.features}),encoding='utf8')
        self.budget_path.write_text(json.dumps({'protocol':'M232_DEVELOPMENT_BUDGET_V1',
            'limit_usd':10,'model_rates_per_million_usd':{MODEL:{'input':1,'output':1}},
            'reserve_multiplier':1.25}),encoding='utf8')
        self.calls=[]

    def _restore(self):
        for k,val in self.saved_env.items():
            if val is None:os.environ.pop(k,None)
            else:os.environ[k]=val

    def _init(self):
        args=SimpleNamespace(out=str(self.exp),problem_file=str(self.problem),
             activation_profile=str(self.profile_path),budget_config=str(self.budget_path))
        with contextlib.redirect_stdout(io.StringIO()):meta.init(args)
        return meta._read(self.exp)

    def _fake_provider(self,wire,timeout):
        self.calls.append(wire)
        return json.dumps({'choices':[{'message':{'content':'{}'}}],
            'usage':{'cost':0,'prompt_tokens':1,'completion_tokens':1}}).encode('utf8')

    def _fake_call(self,root=None,model=MODEL):
        os.environ['FAKG_RESEARCH_ALLOW_PAID']='YES'  # no HTTP: fake provider only
        j=EvolutionJournal(root or self.exp/'ROOTS'/'PRIMARY')
        gateway=DurableModel(j,provider=self._fake_provider,approved=True,
             max_new_calls=1,model=model,max_tokens=32,mode='EXTERNAL')
        return gateway.call('CTRL_D00001','CONTROLLER',None,'mock system',{'test':True})

    def test_m28_real_init_pins_shared_profile_and_budget(self):
        exp,manifest=self._init()
        result=check_m28_experiment(exp,model=MODEL)
        self.assertEqual(result['status'],'M28_ACTIVATION_AND_BUDGET_VERIFIED_NO_PAID')
        self.assertEqual(result['budget_limit_usd'],10)
        self.assertEqual(meta._preflight(exp,manifest)['PRIMARY']['saved_calls'],0)
        self.assertEqual(self._fake_call(),'{}')
        self.assertEqual(len(self.calls),1)
        self.assertEqual(meta._preflight(exp,manifest)['PRIMARY']['saved_calls'],1)

    def test_profile_environment_drift_rejected_before_provider(self):
        self._init()
        os.environ['M232_NAMESPACE_MODE']='COMPACT'
        with self.assertRaisesRegex(RuntimeError,'ENVIRONMENT_DRIFT'):
            self._fake_call()
        self.assertEqual(self.calls,[])
        self.assertEqual(EvolutionJournal(self.exp/'ROOTS'/'PRIMARY').verify().model_calls,{})

    def test_model_mismatch_rejected_before_provider(self):
        self._init()
        with self.assertRaisesRegex(RuntimeError,'MODEL_CHANGED'):
            self._fake_call(model='different-test-model')
        self.assertEqual(self.calls,[])

    def test_budget_change_rejected_before_provider(self):
        self._init()
        budget=self.exp/'M232_DEV_BUDGET.json'
        obj=json.loads(budget.read_text());obj['limit_usd']=100
        budget.write_text(json.dumps(obj),encoding='utf8')
        with self.assertRaisesRegex(RuntimeError,'BUDGET_CONFIG_DRIFT'):
            self._fake_call()
        self.assertEqual(self.calls,[])

    def test_budget_file_missing_fails_closed(self):
        self._init()
        (self.exp/'M232_DEV_BUDGET.json').unlink()
        with self.assertRaisesRegex(RuntimeError,'BUDGET_CONFIG_MISSING'):
            self._fake_call()
        self.assertEqual(self.calls,[])

    def test_profile_manifest_change_rejected(self):
        self._init()
        path=self.exp/'persistent.json';record=json.loads(path.read_text())
        record['activation_profile']['purpose']='mutated'
        path.write_text(json.dumps(record),encoding='utf8')
        with self.assertRaisesRegex(RuntimeError,'MANIFEST_DIGEST_MISMATCH'):
            self._fake_call()
        self.assertEqual(self.calls,[])

    def test_child_root_gets_same_profile_before_model_call(self):
        self._init()
        child=self.exp/'ROOTS'/'SYN_FAKE_CHILD'
        EvolutionJournal(child).init('Finite conditional inference P0')
        self.assertEqual(self._fake_call(root=child),'{}')
        self.assertEqual(len(self.calls),1)
        self.assertEqual(enforce_m28_provider_activation(child,MODEL)['budget_limit_usd'],10)

    def test_legacy_unprofiled_m28_is_readonly_and_no_paid(self):
        exp,old_meta=self._init()
        p=exp/'persistent.json';m=exp/'meta_research.json'
        data=json.loads(p.read_text());data.pop('activation_profile');data.pop('activation_profile_sha256');data.pop('budget_config_sha256');p.write_text(json.dumps(data))
        data=json.loads(m.read_text());data.pop('activation_profile_sha256');data.pop('budget_config_sha256');m.write_text(json.dumps(data))
        self.assertEqual(check_m28_experiment(exp,allow_unprofiled=True)['status'],
                         'M28_LEGACY_UNPROFILED_READONLY_NO_PAID')
        self.assertIn('PRIMARY',meta._preflight(exp,old_meta))
        with self.assertRaisesRegex(RuntimeError,'UNPROFILED_NEW_EXECUTION_FORBIDDEN'):
            self._fake_call()
        with self.assertRaisesRegex(RuntimeError,'UNPROFILED_NEW_EXECUTION_FORBIDDEN'):
            meta.sync(SimpleNamespace(experiment=str(exp),max_roots=2))
        self.assertEqual(self.calls,[])

    def test_full_profile_without_budget_guard_rejected_at_new_init(self):
        data=json.loads(self.profile_path.read_text())
        data['features']['M232_BUDGET_REQUIRED']='NO'
        self.profile_path.write_text(json.dumps(data))
        with self.assertRaisesRegex(Exception,'EXPLICIT_DOLLAR_BUDGET_REQUIRED'):
            self._init()
        self.assertFalse(self.exp.exists())

    def test_on_demand_optimizations_are_selected_not_forced(self):
        changes={'M232_CONTROLLER_DETAIL_MODE':'ON_DEMAND',
                 'M232_NAMESPACE_MODE':'COMPACT',
                 'M233_MODEL_METADATA_MODE':'SEPARATE',
                 'M232_CACHE_POLICY':'SELECTIVE_NO_WRITE',
                 'M232_SYN_PMI_MODE':'SCOPED'}
        data=json.loads(self.profile_path.read_text());data['features'].update(changes)
        self.profile_path.write_text(json.dumps(data))
        os.environ.update(changes)
        self._init()
        result=check_m28_experiment(self.exp,model=MODEL)
        for k,v in changes.items():self.assertEqual(result['features'][k],v)

    def test_explicit_profile_is_mandatory_for_new_init(self):
        with self.assertRaisesRegex(Exception,'EXPLICIT_OPERATOR_PROFILE_REQUIRED_AT_INIT'):
            meta.init(SimpleNamespace(out=str(self.exp),problem_file=str(self.problem),
                activation_profile=None,budget_config=str(self.budget_path)))
        self.assertFalse(self.exp.exists())

if __name__=='__main__':unittest.main()
