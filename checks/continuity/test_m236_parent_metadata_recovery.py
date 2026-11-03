"""M23.6 native no-paid integration: invalid parent -> feedback -> authored correction.

Never connects to a provider, imports historical journals or changes research
policy. All tests use disposable synthetic Journals with saved mock model calls.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from e2core.core import EvolutionJournal
from e2core.engine import Engine, _worker_input
from e2core.m236_parent_recovery import (
    parent_reference_contract, metadata_repair_context, metadata_repair_notices,
    all_asset_publications_rejected, REPAIR_MARKER, REPAIR_PENDING,
)

BAD_PARENT = 'A_CARRY_f16538699604ababcf7e2bbd'
BAD_PARENT_2 = 'A_CARRY_f022ac036548022f66646a9f'


def asset(ident, parents=(), *, delta=''):
    return {
        'id':ident,'kind':'HYPOTHESIS','problem_id':'P0',
        'claim':'Synthetic research claim ('+ident+'); not scientific evidence.',
        'assumptions':'Toy model only','scope':'Toy controlled setting',
        'predictions':[],'limitations':['No empirical test'],
        'parent_ids':list(parents),'delta_from_parents':delta,
        'source_ids':[],
    }


def answer(action='RETURN', assets=(), text='Synthetic independent assessment.'):
    return json.dumps({
        'scientific_text':text,'next_action':action,
        'assets':list(assets),'new_problems':[], 'tool_request':None,
    },ensure_ascii=False)


class SavedMockModel:
    """Model responses are saved as ordinary Journal calls, never billed."""
    def __init__(self, journal, answers):
        self.j=journal
        self.answers=list(answers)
        self.prompts=[]
        self.n_calls=0
    def call(self, ident, actor, work_id, system, payload):
        if actor!='WORKER':raise AssertionError('Unexpected controller model call')
        if not self.answers:raise AssertionError('Unexpected automatic paid/correction call')
        self.prompts.append(payload)
        self.n_calls+=1
        text=self.answers.pop(0)
        self.j.append('MODEL_CALL_INTENT',{
            'id':ident,'actor':actor,'work_id':work_id,
            'request_blob':self.j.blob({'mock_call_id':ident}),
            'model':'MOCK','billing_mode':'MOCK'})
        self.j.append('MODEL_CALL_SAVED',{
            'id':ident,
            'response_blob':self.j.blob({'choices':[{'message':{'content':text},'finish_reason':'stop'}]}),
            'usage':{},
        })
        return text


class M236NativeTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix='m236_no_paid_')
        self.addCleanup(tmp.cleanup)
        self.j=EvolutionJournal(Path(tmp.name)/'root')
        self.j.init('Synthetic test only; no measured physics')
        self.j.evolve('EV_SEED','FRESH',[],{
            'id':'W_SEED','mode':'FRESH','problem_id':'P0',
            'question':'Create a mock predecessor',
            'research_rationale':'Unit-test lineage', 'source_ids':[]},
            'Synthetic baseline')
        self.j.start('W_SEED')
        self.j.step('W_SEED','MODEL_RESPONSE',{'text':'Mock authored precursor'})
        self.j.asset('A_AUTHORIZED','W_SEED','HYPOTHESIS','P0',
                     'Mock predecessor','Synthetic','Synthetic')
        self.j.finish('W_SEED','RETURN','Synthetic completed base')
        self.j.evolve('EV_DEVELOP','DEVELOP',['A_AUTHORIZED'],{
            'id':'W_INFORMED','mode':'INFORMED','problem_id':'P0',
            'question':'Develop precursor','research_rationale':'Synthetic test',
            'source_ids':[]},'Develop conditional mock claim')
        self.j.evolve('EV_OTHER','FRESH',[],{
            'id':'W_FRESH','mode':'FRESH','problem_id':'P0',
            'question':'Separate blind work','research_rationale':'Check isolation',
            'source_ids':[]},'Independent toy')

    def worker(self, answers, wid='W_INFORMED'):
        model=SavedMockModel(self.j,answers)
        return Engine(self.j,model,tool_backend=lambda *_: (_ for _ in ()).throw(
            AssertionError('Unexpected research tool call'))),model,wid

    def test_contract_exact_current_work_and_fresh_isolation(self):
        s=self.j.verify()
        informed=parent_reference_contract(s,s.work['W_INFORMED'])
        self.assertEqual(informed['allowed_registered_parent_ids'],['A_AUTHORIZED'])
        self.assertNotIn(BAD_PARENT,json.dumps(informed))
        fresh=parent_reference_contract(s,s.work['W_FRESH'])
        self.assertEqual(fresh['allowed_registered_parent_ids'],[])
        self.assertNotIn('A_AUTHORIZED',json.dumps(fresh))
        self.assertTrue(fresh['parentless_new_asset_permitted'])
        # No other researcher's rejected submissions can be obtained here.
        fresh_input=_worker_input(self.j,'W_FRESH','NATIVE_RESEARCH_TOOLS')
        self.assertEqual(fresh_input['m236_parent_reference_contract']['allowed_registered_parent_ids'],[])
        self.assertEqual(fresh_input['m235_own_lineage_feedback']['rejected_asset_events'],[])

    def test_invalid_carry_return_is_pending_and_model_corrects_exact_parent(self):
        first=answer(assets=[asset('A_BAD',[BAD_PARENT],delta='Hypothetical')])
        second=answer(assets=[asset('A_FIXED',['A_AUTHORIZED'],delta='New qualified hypothesis')],
                      text='Independently revised scientific relationship to authorized parent.')
        eng,model,wid=self.worker([first,second])
        out=eng.worker_step(wid)
        self.assertEqual(out['status'],REPAIR_PENDING)
        s=self.j.verify()
        self.assertEqual(s.work[wid]['status'],'ACTIVE')
        self.assertNotIn('A_BAD',s.assets)
        self.assertEqual(metadata_repair_notices(self.j,s.work[wid]),1)
        self.assertEqual(model.n_calls,1)
        self.assertTrue(any(
            json.loads(self.j.raw(st['raw_blob'])).get('status')==REPAIR_MARKER
            for st in s.work[wid]['steps'] if st['kind']=='OUTPUT_VALIDATION'))
        out=eng.worker_step(wid)
        self.assertEqual(out['status'],'RETURN')
        s=self.j.verify()
        self.assertEqual(s.assets['A_FIXED']['parent_ids'],['A_AUTHORIZED'])
        self.assertEqual(s.work[wid]['status'],'DONE')
        self.assertNotIn('A_BAD',s.assets)
        self.assertEqual(len(s.model_calls),2)
        second_prompt=model.prompts[1]
        self.assertEqual(second_prompt['m236_parent_reference_contract']['allowed_registered_parent_ids'],['A_AUTHORIZED'])
        self.assertTrue(second_prompt['m236_metadata_repair_context']['previous_metadata_delivery_repair_notice'])
        self.assertIn('A_BAD',[v['model_asset_id'] for v in second_prompt['m235_own_lineage_feedback']['rejected_asset_events']])
        self.assertIn(BAD_PARENT,json.dumps(second_prompt['m235_own_lineage_feedback']))
        self.assertTrue(second_prompt['m236_metadata_repair_context']['may_withdraw_rejected_asset'])

    def test_same_rejected_id_can_be_reproposed_by_model_with_valid_parent(self):
        first=answer(assets=[asset('A_SAME_ID',[BAD_PARENT],delta='Toy')])
        second=answer(assets=[asset('A_SAME_ID',['A_AUTHORIZED'],delta='Revised relation')],
                      text='Author explicitly corrects reference; no auto-aliasing.')
        eng,model,wid=self.worker([first,second])
        self.assertEqual(eng.worker_step(wid)['status'],REPAIR_PENDING)
        self.assertEqual(eng.worker_step(wid)['status'],'RETURN')
        s=self.j.verify()
        self.assertIn('A_SAME_ID',s.assets)
        self.assertEqual(s.assets['A_SAME_ID']['parent_ids'],['A_AUTHORIZED'])
        history=model.prompts[1]['m235_own_lineage_feedback']['rejected_asset_events']
        self.assertEqual(history[0]['error'],'BAD_ASSET_PARENTS')
        self.assertEqual(metadata_repair_notices(self.j,s.work[wid]),1)

    def test_existing_but_unpinned_parent_is_not_authorized(self):
        self.j.evolve('EV_OTHER_AUTH','FRESH',[],{
            'id':'W_OTHER','mode':'FRESH','problem_id':'P0',
            'question':'Different independent problem','research_rationale':'Synthetic',
            'source_ids':[]}, 'Independent test')
        self.j.start('W_OTHER')
        self.j.step('W_OTHER','MODEL_RESPONSE',{'text':'Mock unrelated result'})
        self.j.asset('A_OTHER','W_OTHER','HYPOTHESIS','P0',
                     'Another toy result','Only toy','Toy')
        self.j.finish('W_OTHER','RETURN','Toy')
        eng,model,wid=self.worker([
            answer(assets=[asset('A_UNAUTHORIZED',['A_OTHER'],delta='Toy')]),
            answer(assets=[asset('A_AUTHORIZED_CHILD',['A_AUTHORIZED'],delta='Toy revised')])])
        self.assertEqual(eng.worker_step(wid)['status'],REPAIR_PENDING)
        self.assertEqual(eng.worker_step(wid)['status'],'RETURN')
        second=model.prompts[1]
        self.assertNotIn('A_OTHER',second['m236_parent_reference_contract']['allowed_registered_parent_ids'])
        errors=[x['error'] for x in second['m235_own_lineage_feedback']['rejected_asset_events']]
        self.assertIn('UNAUTHORIZED_ASSET_PARENT',errors)
        self.assertIn('A_AUTHORIZED_CHILD',self.j.verify().assets)
        self.assertNotIn('A_UNAUTHORIZED',self.j.verify().assets)

    def test_repeated_all_rejected_final_blocks_without_third_call(self):
        bad=answer(assets=[asset('A_REJECT_1',[BAD_PARENT],delta='Toy')])
        bad2=answer(assets=[asset('A_REJECT_2',[BAD_PARENT_2],delta='Toy')])
        eng,model,wid=self.worker([bad,bad2])
        self.assertEqual(eng.worker_step(wid)['status'],REPAIR_PENDING)
        self.assertEqual(eng.worker_step(wid)['status'],'BLOCKED_METADATA')
        self.assertEqual(model.n_calls,2)
        s=self.j.verify()
        self.assertEqual(s.work[wid]['status'],'DONE')
        self.assertEqual(s.work[wid]['outcome'],'BLOCKED')
        self.assertEqual(metadata_repair_notices(self.j,s.work[wid]),1)
        self.assertNotIn('A_REJECT_1',s.assets)
        self.assertNotIn('A_REJECT_2',s.assets)

    def test_worker_can_withdraw_asset_and_return_without_compulsory_repair(self):
        eng,model,wid=self.worker([
            answer('HOLD',[asset('A_BAD_HOLD',[BAD_PARENT],delta='Toy')]),
            answer('HOLD',[],text='Previous asset withdrawn; evidence is inadequate.')])
        self.assertEqual(eng.worker_step(wid)['status'],REPAIR_PENDING)
        self.assertEqual(eng.worker_step(wid)['status'],'HOLD')
        s=self.j.verify()
        self.assertEqual(s.work[wid]['status'],'DONE')
        self.assertEqual(s.work[wid]['outcome'],'HOLD')
        self.assertNotIn('A_BAD_HOLD',s.assets)
        self.assertEqual(model.n_calls,2)

    def test_independent_valid_asset_is_accepted_without_parent_forcing(self):
        eng,model,wid=self.worker([answer(assets=[asset('A_STANDALONE')])],wid='W_FRESH')
        self.assertEqual(eng.worker_step(wid)['status'],'RETURN')
        self.assertEqual(self.j.verify().assets['A_STANDALONE']['parent_ids'],[])
        self.assertEqual(model.n_calls,1)

    def test_partial_acceptance_is_not_forced_to_extra_call(self):
        eng,model,wid=self.worker([answer(assets=[
            asset('A_VALID',['A_AUTHORIZED'],delta='Synthetic extension'),
            asset('A_INVALID',[BAD_PARENT],delta='Synthetic invalid')])])
        result=eng.worker_step(wid)
        self.assertEqual(result['status'],'RETURN')
        self.assertEqual(result['published'],1)
        self.assertEqual(result['rejected_metadata'],1)
        s=self.j.verify()
        self.assertIn('A_VALID',s.assets)
        self.assertNotIn('A_INVALID',s.assets)
        self.assertEqual(model.n_calls,1)
        self.assertEqual(metadata_repair_notices(self.j,s.work[wid]),0)

    def test_continue_with_invalid_metadata_not_forced_to_return(self):
        eng,model,wid=self.worker([
            answer('CONTINUE',[asset('A_TMP',[BAD_PARENT],delta='Toy')]),
            answer('RETURN',[],text='Continue research and finish without claiming success')])
        first=eng.worker_step(wid)
        self.assertEqual(first['status'],'CONTINUE')
        self.assertEqual(metadata_repair_notices(self.j,self.j.verify().work[wid]),0)
        self.assertEqual(eng.worker_step(wid)['status'],'RETURN')
        self.assertEqual(model.n_calls,2)
        self.assertNotIn('A_TMP',self.j.verify().assets)

    def test_repair_notice_is_durable_across_engine_restart(self):
        eng1,model1,wid=self.worker([answer(assets=[asset('A_1',[BAD_PARENT],delta='Toy')])])
        self.assertEqual(eng1.worker_step(wid)['status'],REPAIR_PENDING)
        eng2,model2,wid=self.worker([answer(assets=[asset('A_2',[BAD_PARENT],delta='Toy')])])
        self.assertEqual(eng2.worker_step(wid)['status'],'BLOCKED_METADATA')
        self.assertEqual(model1.n_calls,1)
        self.assertEqual(model2.n_calls,1)
        self.assertEqual(len(self.j.verify().model_calls),2)

    def test_boolean_repair_predicate_only_when_no_asset_published(self):
        self.assertTrue(all_asset_publications_rejected(
            [{'kind':'ASSET','error':'BAD_ASSET_PARENTS'}],[]))
        self.assertTrue(all_asset_publications_rejected(
            [{'kind':'ASSET','error':'BAD_ASSET_PARENTS'}],[('PROBLEM_CREATED',{})]))
        self.assertFalse(all_asset_publications_rejected(
            [{'kind':'ASSET','error':'BAD_ASSET_PARENTS'}],[('ASSET_PUBLISHED',{})]))
        self.assertFalse(all_asset_publications_rejected(
            [{'kind':'PROBLEM','error':'PARENTS_NOT_LIST'}],[]))


if __name__=='__main__':
    unittest.main()
