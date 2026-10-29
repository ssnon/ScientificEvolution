import json, os, pathlib, tempfile, unittest
from unittest.mock import patch
from e2core.core import EvolutionJournal
from e2core.engine import Engine, _external_context
from e2core.provider import DurableModel
from e2core.e3_evolution_audit import audit


def assess(reason,*,research='CONTINUING'):
    return {'objective_status':'UNRESOLVED','research_status':research,
            'objective_coverage':'NO_OBJECTIVE_RESULT','resolved_scope':'none',
            'supporting_asset_ids':[],'remaining_questions':['Mock only'],
            'untried_approaches_considered':[],'reason':reason}


def action(eid,op,parents,wid,mode,question):
    return {'id':eid,'operation':op,'asset_ids':parents,'reason':'Synthetic research action, not scientific validation',
       'work':{'id':wid,'mode':mode,'problem_id':'P0',
          'question':question,'research_rationale':'Test end-to-end inherited evidence','source_ids':[]}}


def asset(aid,kind,claim,parents=()):
    return {'id':aid,'kind':kind,'problem_id':'P0','claim':claim,
        'assumptions':'Illustrative fiction for runtime test only',
        'scope':'No natural system; synthetic mechanism toy','predictions':['Distinct conditional observable'],
        'limitations':['Not experimental evidence'], 'source_ids':[],
        'parent_ids':list(parents),'delta_from_parents':'Scoped, revised predictions after explicit parent comparison' if parents else ''}


class LiveLineageMockProvider:
    def __init__(self):self.request_log=[]
    def __call__(self,wire,timeout=180):
        req=json.loads(wire);user=json.loads(req['messages'][1]['content'])
        self.request_log.append(user)
        if 'pinned_input' in user:
            wid=user['pinned_input']['work']['id'];parents=user['pinned_input']['parent_assets']
            if wid=='W_A':obj={'scientific_text':'Hypothetical A mechanism; only toy','next_action':'RETURN',
                'assets':[asset('A_H','HYPOTHESIS','Invented mechanism H')],'new_problems':[],'tool_request':None}
            elif wid=='W_B':
                assert not parents and all(x['kind']=='PRIMARY' for x in user['pinned_input']['source_entries'])
                obj={'scientific_text':'Independent toy N, not influenced by H','next_action':'RETURN',
                     'assets':[asset('A_N','NULL_MODEL','Competing invented mechanism N')],'new_problems':[],'tool_request':None}
            elif wid=='W_DEV':
                assert [a['id'] for a in parents]==['A_H']
                obj={'scientific_text':'Narrow H with new predicted sign; unverified','next_action':'RETURN',
                  'assets':[asset('A_H2','PREDICTION','Conditional sign reversal for narrow H',['A_H'])],
                  'new_problems':[],'tool_request':None}
            elif wid=='W_FUSE':
                assert {a['id'] for a in parents}=={'A_H','A_N'}
                obj={'scientific_text':'Joint comparison depends on actual tool output','next_action':'CONTINUE',
                     'assets':[],'new_problems':[],
                     'tool_request':{'kind':'verified_calculation','arguments':{'expressions':{'sum':'x+y'},'scenarios':[{'x':2,'y':3}]}}}
                if any(st['kind']=='TOOL_RESULT' for st in user['own_prior_steps']):
                    last=[st for st in user['own_prior_steps'] if st['kind']=='TOOL_RESULT'][-1]
                    assert last['content']['result']['status'] in {'VERIFIED','DELIVERED'} or last['content']['result']['results'][0]['computed']['sum']==5
                    obj={'scientific_text':'Toy numerical witness from executed calculation, not new physics',
                      'next_action':'RETURN', 'assets':[asset('A_FUSE','PREDICTION','New mock comparative prediction after computation',['A_H','A_N'])],
                      'new_problems':[],'tool_request':None}
            else:raise AssertionError(wid)
        else:
            names={a['id'] for a in user['assets']}
            if not names:actions=[action('EV_A','FRESH',[],'W_A','FRESH','Explore toy A'),action('EV_B','FRESH',[],'W_B','FRESH','Independent toy B')]
            elif 'A_H' in names and 'A_N' not in names:actions=[action('EV_DEV','DEVELOP',['A_H'],'W_DEV','INFORMED','Recompute scoped H')]
            elif 'A_N' in names and 'A_FUSE' not in names and 'A_H2' not in names:actions=[action('EV_FUSE','FUSE',['A_H','A_N'],'W_FUSE','INFORMED','Compare H and N')]
            elif 'A_FUSE' in names:actions=[]
            else:actions=[]
            stop='A_FUSE' in names
            obj={'rationale':'Synthetic decision, does not imply discovery',
                 'actions':actions,'new_problems':[],'reviews':[],
                 'disposition':'HOLD_WITH_RATIONALE' if stop else 'ONGOING',
                 'unresolved_opportunities':['Real empirical evidence absent'],
                 'objective_assessment':assess('End of scripted toy' if stop else 'Need to run queued toy workers',
                                               research='PAUSED_LOW_INFORMATION' if stop else 'CONTINUING')}
            if 'A_H' in names and 'A_N' not in names:
                assert 'W_B' in user['frontier']['queued']
                assert any(x['id']=='A_H' for x in user['unreviewed_frontier_events'])
            if 'A_FUSE' in names:
                assert any(a['id']=='A_FUSE' and a['parent_ids']==['A_H','A_N'] for a in user['assets'])
        return json.dumps({'choices':[{'message':{'content':json.dumps(obj)}}]}).encode()


class E3ScientificEvolution(unittest.TestCase):
    def test_scripted_live_controller_reacts_before_initial_fresh_cohort_finished(self):
        with tempfile.TemporaryDirectory() as d:
            j=EvolutionJournal(pathlib.Path(d)/'fresh');j.init('Synthetic mechanism study; no actual physics',origin='MOCK_ONLY')
            j.append('R5_POLICY_ACTIVATED',{'policy':'OBJECTIVE_AND_DISPOSITION_V1'})
            p=LiveLineageMockProvider()
            with patch.dict(os.environ,{'FAKG_RESEARCH_ALLOW_PAID':'YES'}):
                gateway=DurableModel(j,provider=p,approved=True,max_new_calls=30,mode='MOCK')
                engine=Engine(j,gateway,serial_fair=True)
                result=engine.run(max_iterations=25,max_parallel=1)
            self.assertEqual(result['status'],'SCIENTIFIC_DISPOSITION_PROPOSED')
            s=j.verify()
            self.assertEqual(len(s.controller_decisions),5)
            self.assertEqual(len(s.assets),4)
            self.assertEqual(len(s.tool_results),1)
            self.assertEqual(s.objective_assessments[-1]['research_status'],'PAUSED_LOW_INFORMATION')
            self.assertEqual(s.assets['A_FUSE']['parent_ids'],['A_H','A_N'])
            self.assertIn('Conditional sign reversal',s.assets['A_H2']['claim'])
            rows=j._events();seq=lambda kind, id:next(e['seq'] for e in rows if e['kind']==kind and e['payload'].get('id')==id)
            self.assertLess(seq('EVOLUTION_APPLIED','EV_DEV'),seq('WORK_STARTED','W_B'))
            self.assertLess(seq('EVOLUTION_APPLIED','EV_FUSE'),seq('WORK_STARTED','W_DEV'))
            self.assertLess(seq('WORK_FINISHED','W_B'),seq('ASSET_PUBLISHED','A_FUSE'))
            r=audit(j.root)
            self.assertGreaterEqual(r['cross_researcher_derived_work_count'],2)
            self.assertEqual(r['cross_researcher_derived_asset_count'],2)
            self.assertFalse(r['scientific_level_ii_certified'])
            self.assertFalse(any(c['billing_mode']=='EXTERNAL' for c in s.model_calls.values()))
            # FRESH, including new FRESH, receives no earlier AI claims.
            first_inputs=[x for x in p.request_log if 'pinned_input' in x and x['pinned_input']['work']['mode']=='FRESH']
            self.assertEqual(len(first_inputs),2)
            self.assertTrue(all(not x['pinned_input']['parent_assets'] for x in first_inputs))

    def test_no_new_published_intermediate_event_does_not_trigger_controller(self):
        with tempfile.TemporaryDirectory() as d:
            j=EvolutionJournal(pathlib.Path(d)/'j');j.init('Mock no action')
            j.evolve('E_W','FRESH',[],{'id':'W','mode':'FRESH','problem_id':'P0',
                'question':'Toy','research_rationale':'Toy','source_ids':[]},'Mock')
            self.assertFalse(Engine(j,object(),serial_fair=True)._should_controller_run())
            j.start('W');self.assertFalse(Engine(j,object(),serial_fair=True)._should_controller_run())

if __name__=='__main__':unittest.main()

class E3InheritedEvidence(unittest.TestCase):
    def test_informed_child_retains_exact_parent_tool_source_without_reexecution(self):
        with tempfile.TemporaryDirectory() as d:
            j=EvolutionJournal(pathlib.Path(d)/'j');j.init('Synthetic study')
            j.append('R5_POLICY_ACTIVATED',{'policy':'OBJECTIVE_AND_DISPOSITION_V1'})
            base={'id':'W1','mode':'FRESH','problem_id':'P0','question':'Test fact','research_rationale':'Toy','source_ids':[]}
            j.evolve('E1','FRESH',[],base,'A new independent research arm')
            j.start('W1');j.step('W1','MODEL_RESPONSE',{'text':'A synthetic toy observation'})
            source={'tool_id':'TOOL_W1_0001','work_id':'W1','request':{'kind':'literature_research'},'result':{'status':'DELIVERED'},'evidence_class':'OA_FULLTEXT_TEXT'}
            j.append('TOOL_RECORDED',{'id':'TOOL_W1_0001','work_id':'W1',
                'request_blob':j.blob(source['request']),'result_blob':j.blob(source['result'])})
            j.append('SOURCE_REGISTERED',{'id':'SRC_CHILD_INPUT','kind':'TOOL_RESULT','work_id':'W1',
                'blob':j.blob(source),'description':'Toy tool response only'})
            j.asset('A_PARENT','W1','LITERATURE_CLAIM','P0','A toy empirical claim','Only toy', 'Toy',source_ids=['SRC_CHILD_INPUT'])
            j.finish('W1','RETURN','Toy')
            j.evolve('E2','DEVELOP',['A_PARENT'],{'id':'W2','mode':'INFORMED','problem_id':'P0',
                'question':'Develop claim','research_rationale':'Read inherited source','source_ids':[]},'Develop published claim')
            j.start('W2')
            j.step('W2','MODEL_RESPONSE',{'text':'Qualified toy claim using parent source'})
            j.asset('A_CHILD','W2','HYPOTHESIS','P0','Qualified claim','Toy assumption','Toy',
                source_ids=['SRC_CHILD_INPUT'],parent_ids=['A_PARENT'],delta_from_parents='Narrowed scope')
            r=j.verify()
            self.assertEqual(r.assets['A_CHILD']['source_ids'],['SRC_CHILD_INPUT'])
            self.assertEqual(r.sources['SRC_CHILD_INPUT']['work_id'],'W1')
            self.assertEqual(len(r.tool_results),1)  # exact synthetic receipt preserved, not a real experiment

class E3ParallelResearch(unittest.TestCase):
    def test_two_independent_workers_make_overlapping_provider_requests(self):
        import threading
        with tempfile.TemporaryDirectory() as d:
            j=EvolutionJournal(pathlib.Path(d)/'j');j.init('Mock parallel')
            for wid in ['A','B']:
                j.evolve('E_'+wid,'FRESH',[],{'id':wid,'mode':'FRESH','problem_id':'P0',
                    'question':'Separate synthetic task','research_rationale':'Independent toy','source_ids':[]},'Synthetic separate research')
            barrier=threading.Barrier(2,timeout=8)
            requested=[]
            def reply(wire,timeout=180):
                context=json.loads(json.loads(wire)['messages'][1]['content'])
                wid=context['pinned_input']['work']['id']
                requested.append(wid)
                barrier.wait()  # would timeout if execution were serial
                obj={'scientific_text':'Concurrent but entirely synthetic '+wid,
                    'next_action':'RETURN','assets':[asset('A_'+wid,'HYPOTHESIS','Synthetic '+wid)],
                    'new_problems':[],'tool_request':None}
                return json.dumps({'choices':[{'message':{'content':json.dumps(obj)}}]}).encode()
            with patch.dict(os.environ,{'FAKG_RESEARCH_ALLOW_PAID':'YES'}):
                gw=DurableModel(j,provider=reply,approved=True,max_new_calls=2,mode='MOCK')
                r=Engine(j,gw,serial_fair=False).run(max_iterations=1,max_parallel=2)
            self.assertEqual(set(requested),{'A','B'})
            self.assertEqual(set(j.verify().assets),{'A_A','A_B'})
            self.assertEqual(r['status'],'OPERATIONAL_RUN_BOUNDARY')
