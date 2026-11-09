"""M28-A1 native no-paid Journal/Controller/root-creation acceptance.

Does NOT demonstrate that a real LLM makes scientifically good choices.
"""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from e2core.core import EvolutionJournal, EvidenceError, canon
from e2core.engine import Engine, controller_plan
from e2core.meta_autonomy import (
    POLICY, MODE_BLIND, MODE_TARGETED, _binding, _prepare_stage,
    _root_name, materialize_requests, recover_committed_requests,
    verify_receipts,
)


def _decision(requests=None, *, existing_work=False):
    return {
        'rationale': 'Model-authored scientific and organizational judgement, not a certificate',
        'new_problems': [], 'reviews': [],
        'actions': ([{
            'id': 'EV_scientific_continuation', 'operation':'DECOMPOSE',
            'asset_ids':[], 'reason':'Investigate a well specified subproblem',
            'work':{'id':'W_scientific_continuation','mode':'INFORMED','problem_id':'P0',
                    'question':'Compute a reproducible conditional test',
                    'research_rationale':'A potentially falsifiable test',
                    'source_ids':[]},
        }] if existing_work else []),
        'portfolio_decisions': [],
        'organization_requests': list(requests or []),
        'disposition':'ONGOING',
        'unresolved_opportunities': [],
        'objective_assessment': {
            'objective_status':'UNRESOLVED','research_status':'CONTINUING',
            'resolved_scope':'none','objective_coverage':'NO_OBJECTIVE_RESULT',
            'supporting_asset_ids':[], 'remaining_questions':['Scientific P0 remains open'],
            'untried_approaches_considered':[],
            'reason':'Research remains possible; no empirical truth is inferred',
        },
    }


def _request(mode=MODE_BLIND, targets=(), rid='ORG_original_001'):
    return {'id':rid, 'mode':mode,
            'purpose':'Independent reasoning could expose a different explanation',
            'evidence_asset_ids': [], 'target_asset_ids':list(targets)}


class FakeSavedControllerModel:
    """Stores actual SAVED events and returns a scripted controller envelope."""
    def __init__(self,j,response):
        self.j=j;self.response=response;self.prompts=[];self.new_calls=0
    def call(self, ident, actor, work_id, prompt, payload):
        self.prompts.append((ident, prompt, payload))
        self.j.append('MODEL_CALL_INTENT', {
            'id':ident,'actor':actor,'work_id':work_id,
            'request_blob':self.j.blob(canon({'prompt':prompt,'payload':payload})),
            'model':'OFFLINE_SCRIPTED_TEST','billing_mode':'MOCK'})
        self.j.append('MODEL_CALL_SAVED', {'id':ident,
            'response_blob':self.j.blob(canon({'scripted':self.response})),
            'usage':{'prompt_tokens':0,'completion_tokens':0,'cost':0}})
        return json.dumps(self.response)


class TestM28A1(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.exp=Path(self.temp.name)/'META_EXPERIMENT'
        self.roots=self.exp/'ROOTS'
        self.roots.mkdir(parents=True)
        self.parent_root=self.roots/'PRIMARY'
        self.j=EvolutionJournal(self.parent_root)
        self.j.init('Original untouched P0 question',criteria='External review-worthy result')
        self.j.append('R5_POLICY_ACTIVATED', {'policy':'OBJECTIVE_AND_DISPOSITION_V1'})
        self.j.append('E3R1_POLICY_ACTIVATED', {'policy':'PORTFOLIO_DECISIONS_V1'})
        self.j.append('META_RESEARCH_AUTONOMY_ACTIVATED', {'policy':POLICY})
    def tearDown(self):
        self.temp.cleanup()

    def _commit(self,raw):
        model=FakeSavedControllerModel(self.j,raw)
        engine=Engine(self.j,model)
        result=engine.controller('D00001')
        self.assertEqual(result['status'],'CONTROLLER_COMMITTED',result)
        self.assertEqual(self.j.verify().controller_decisions[0]['id'],'D00001')
        return model

    def _materialize(self):
        return materialize_requests(self.exp,self.parent_root,8)

    def test_no_organization_change_keeps_existing_scientific_work(self):
        model=self._commit(_decision(existing_work=True))
        self.assertIn('M28-A1 META-RESEARCH AUTONOMY',model.prompts[0][1])
        self.assertEqual(self._materialize(),[])
        state=self.j.verify()
        self.assertEqual(state.work['W_scientific_continuation']['status'],'QUEUED')
        self.assertEqual(list(self.roots.iterdir()),[self.parent_root])
        self.assertFalse(state.organization_requests)

    def test_blind_spawn_is_real_and_fully_isolated_from_prior_ai(self):
        self._commit(_decision([_request()]))
        original=self.j.verify()
        receipts=self._materialize()
        self.assertEqual(len(receipts),1)
        child=EvolutionJournal(Path(receipts[0]['root']))
        s=child.verify()
        self.assertEqual(s.program['problem'],original.program['problem'])
        self.assertEqual(s.program['origin'],'INDEPENDENT_UNSEEDED_FRESH_COHORT')
        self.assertTrue(s.meta_research_autonomy)
        self.assertFalse(s.assets or s.sources or s.work or s.model_calls)
        self.assertEqual(len(s.problems),1)
        self.assertEqual(verify_receipts(self.exp,self.parent_root),1)
        self.assertFalse(list(self.exp.glob('CYCLE_*')))
        self.assertFalse((self.exp/'POPULATION').exists())
        self.assertFalse(self.j.verify().assets)
        self.assertEqual(self._materialize(),[])
        self.assertEqual(len(list(self.roots.iterdir())),2)

    def _add_historical_target(self):
        self.j.add_source('SRC_parent_claim','HISTORICAL_AI',{'unverified':True},
                          'A separate AI-proposed hypothesis, not experimental fact')
        self.j.append('HISTORICAL_ASSET_INDEXED', {
            'id':'A_target_claim','kind':'HYPOTHESIS','problem_id':'P0',
            'parent_ids':[], 'claim':'Charge state changes the observed signal',
            'scope':'Conditional model','assumptions':'Toy finite-state hypothesis',
            'predictions':[],'limitations':['Not measured'],
            'source_ids':['SRC_parent_claim'],
        })

    def test_targeted_challenge_is_not_misrepresented_as_blind(self):
        self._add_historical_target()
        self._commit(_decision([_request(MODE_TARGETED,['A_target_claim'])]))
        rec=self._materialize()[0]
        child=EvolutionJournal(rec['root']).verify()
        self.assertEqual(child.program['origin'],'TARGETED_INDEPENDENT_CHALLENGE_NOT_BLIND')
        self.assertEqual(len(child.assets),1)
        self.assertEqual(len(child.sources),1)
        a=next(iter(child.assets.values()))
        self.assertIn('not original-P0-blind', ' '.join(a['limitations']))
        self.assertEqual(verify_receipts(self.exp,self.parent_root),1)

    def test_target_requires_real_parent_asset(self):
        self._add_historical_target()
        bad=_request(MODE_TARGETED,[])
        model=FakeSavedControllerModel(self.j,_decision([bad]))
        result=Engine(self.j,model).controller('D00001')
        self.assertEqual(result['status'],'CONTROLLER_PLAN_REJECTED')
        self.assertFalse(self.j.verify().organization_requests)
        self.assertEqual(self._materialize(),[])

    def test_controller_can_request_spawn_with_existing_work_still_queued(self):
        self._commit(_decision([_request()],existing_work=True))
        self.assertEqual(len(self._materialize()),1)
        self.assertEqual(self.j.verify().work['W_scientific_continuation']['status'],'QUEUED')

    def test_completed_staging_crash_is_recoverable_without_duplicate_root(self):
        self._commit(_decision([_request()]))
        req=next(iter(self.j.verify().organization_requests.values()))
        binding=_binding(self.parent_root,self.j,req)
        dest=self.roots/_root_name(req)
        stage=self.roots/(dest.name+'.STAGING')
        _prepare_stage(stage,binding,self.j.verify())
        self.assertTrue(stage.is_dir())
        made=self._materialize()
        self.assertEqual(len(made),1)
        self.assertFalse(stage.exists())
        self.assertEqual(self._materialize(),[])
        self.assertEqual(verify_receipts(self.exp,self.parent_root),1)

    def test_saved_controller_crash_recovery_is_not_a_new_model_call(self):
        raw=_decision([_request()])
        model=FakeSavedControllerModel(self.j,raw)
        # Durable model call and Controller decision exist; crash occurred
        # after the Controller event but before the organization event.
        model.call('CTRL_D00001','CONTROLLER',None,'mock prompt',{})
        self.j.append('CONTROLLER_DECISION', {
            'id':'D00001','call_id':'CTRL_D00001',
            'parsed_blob':self.j.blob(raw),'rationale':raw['rationale']})
        before=len(self.j.verify().model_calls)
        self.assertEqual(recover_committed_requests(self.j),['ORG_original_001'])
        self.assertEqual(len(self.j.verify().model_calls),before)
        self.assertEqual(recover_committed_requests(self.j),[])
        self.assertEqual(len(self._materialize()),1)

    def test_unactivated_root_cannot_accept_organization_requests(self):
        legacy=EvolutionJournal(self.roots/'LEGACY')
        legacy.init('another P0')
        legacy.append('R5_POLICY_ACTIVATED',{'policy':'OBJECTIVE_AND_DISPOSITION_V1'})
        legacy.append('E3R1_POLICY_ACTIVATED',{'policy':'PORTFOLIO_DECISIONS_V1'})
        model=FakeSavedControllerModel(legacy,_decision([_request()]))
        result=Engine(legacy,model).controller('D00001')
        self.assertEqual(result['status'],'CONTROLLER_PLAN_REJECTED')
        self.assertFalse(legacy.verify().organization_requests)

    def test_unknown_meta_request_cannot_be_materialized_as_sci_success(self):
        self._commit(_decision([_request()]))
        self._materialize()
        self.assertEqual(self.j.verify().organization_materialized['ORG_original_001']['execution_status'],
                         'ROOT_INITIALIZED_NO_SCIENCE_EXECUTED')
        self.assertEqual(self.j.verify().program_reviews[-1]['scientific_status'],'ONGOING')


if __name__=='__main__':
    unittest.main()
