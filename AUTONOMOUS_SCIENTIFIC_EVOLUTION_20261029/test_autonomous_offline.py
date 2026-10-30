#!/usr/bin/env python3
"""Offline model-return, model-caching, council, and local-stop tests.
No network, paid model, or user's research root is accessed.
"""
import json, tempfile, pathlib, hashlib, types, sys, os
from types import SimpleNamespace
import autonomous_population as a
import persistent_population as pp
from test_offline import FakeJournal as BasicJournal,canon,sha

class Journal(BasicJournal):
    store={}
    def __init__(self,root):
        self.root=pathlib.Path(root).resolve()
        k=str(self.root)
        if k not in self.store:
            self.store[k]=SimpleNamespace(program=None,problems={},assets={},sources={},work={},
                program_reviews=[],controller_decisions=[],model_calls={},tool_results={},rows=[])
        self.s=self.store[k];self.rows=self.s.rows
    def append(self,kind,payload):
        row=super().append(kind,payload)
        if kind=='MODEL_CALL_INTENT':self.s.model_calls[payload['id']]={**payload,'state':'INTENT'}
        if kind=='MODEL_CALL_SAVED':self.s.model_calls[payload['id']].update(state='SAVED',response_blob=payload['response_blob'])
        if kind=='CONTROLLER_DECISION':self.s.controller_decisions.append(payload)
        if kind=='PROGRAM_REVIEWED':self.s.program_reviews.append(payload)
        return row

class Model:
    responses=[];call_count=0
    def __init__(self,j,**kw):self.j=j
    def call(self,ident,actor,work_id,prompt,context):
        old=self.j.verify().model_calls.get(ident)
        if old:
            assert old['state']=='SAVED'
            return json.loads(self.j.raw(old['response_blob']))['choices'][0]['message']['content']
        Model.call_count+=1
        if not Model.responses:raise AssertionError('Missing mock model reply')
        msg=json.dumps(Model.responses.pop(0),ensure_ascii=False)
        wire={'model':'mock','messages':[{'role':'system','content':prompt},
            {'role':'user','content':json.dumps(context,ensure_ascii=False)}]}
        self.j.append('MODEL_CALL_INTENT',{'id':ident,'actor':actor,'request_blob':self.j.blob(wire)})
        self.j.append('MODEL_CALL_SAVED',{'id':ident,'response_blob':self.j.blob({'choices':[{'message':{'content':msg}}]})})
        return msg

def setup():
    home=tempfile.TemporaryDirectory(prefix='autonomous-tests-')
    root=pathlib.Path(home.name)
    base=Journal(root/'BASE_000');base.init('Exact scientific problem P0')
    manifest={'protocol':pp.PROTOCOL,'root':str(root),'original_source':'/source/unchanged',
        'source_head':{'events':1},'P0_sha256':hashlib.sha256(b'Exact scientific problem P0').hexdigest(),
        'generation_zero_base':str(root/'BASE_000')}
    pp.newwrite(root/'persistent.json',manifest)
    a.pop.gen.modules=lambda: SimpleNamespace(J=Journal,sha=sha,canon=canon)
    old_module=sys.modules.get('e2core')
    old_provider=sys.modules.get('e2core.provider')
    sys.modules['e2core']=types.ModuleType('e2core')
    sys.modules['e2core.provider']=types.SimpleNamespace(DurableModel=Model)
    a.init_meta(SimpleNamespace(experiment=str(root),paid=False))
    return home,root,old_module,old_provider

def restore(home,old,provider):
    if old is None:sys.modules.pop('e2core',None)
    else:sys.modules['e2core']=old
    if provider is None:sys.modules.pop('e2core.provider',None)
    else:sys.modules['e2core.provider']=provider
    home.cleanup()

def test_terminal_journal_and_no_rebilling():
    tmp,root,o,p=setup()
    try:
        mods=a.pop.gen.modules();Model.call_count=0
        decision={'decision':'SCIENTIFIC_HOLD','rationale':'Independent frontiers have been examined',
            'inherited_findings_considered':['A1'],'new_scientific_delta':'No non-redundant mechanism remains',
            'remaining_opportunities':[],'unresolved_uncertainties':['No laboratory data'],
            'termination_scope':'No useful accessible continuation at present'}
        review={'assessment':'CHALLENGE_TERMINAL','rationale':'A narrow idea may remain',
            'unexplored_material_frontiers':['Independent kinetic test']}
        final={'decision':'CONFIRM_TERMINAL','rationale':'The narrow idea duplicates established claims',
            'remaining_opportunities':[],'termination_scope':'Scoped resource-limited closure'}
        Model.responses=[decision,review,final]
        ctx={'stage':'POPULATION','cycle_number':1,'current_research':{'head':'hash'}}
        proposed,i,new=a.model_decision(mods,root,'STEER',ctx,a.S_PROMPT,a.POP_CHOICES,16000,'mock')
        assert new and proposed==decision
        _,_,r=a.terminal_adjudication(mods,root,ctx,proposed,i,SimpleNamespace(max_tokens=16000,model='mock'))
        assert r==review
        assert Model.call_count==3
        assert a.last_meta_outcome(mods,root)[1]['decision']=='CONFIRM_TERMINAL'
        a.model_decision(mods,root,'STEER',ctx,a.S_PROMPT,a.POP_CHOICES,16000,'mock')
        assert Model.call_count==3
        j,s,_=a.meta_check(mods,root)
        assert len(s.controller_decisions)==3
        assert len(s.program_reviews)==3
        assert s.program_reviews[0]['scientific_status']=='ONGOING' # proposal is provisional
        assert s.program_reviews[-1]['scientific_status']=='HOLD_WITH_RATIONALE'
        assert all(c['state']=='SAVED' for c in s.model_calls.values())
        print('PASS: model-authored terminal, skeptical review, adjudication, exactly-once saved calls')
    finally:restore(tmp,o,p)

def test_stop_and_no_approval():
    tmp,root,o,p=setup()
    try:
        (root/'STOP_REQUESTED').touch()
        assert a.ensure_not_stopped(root) is False
        (root/'STOP_REQUESTED').unlink()
        assert a.ensure_not_stopped(root) is True
        try:a.run(SimpleNamespace(paid=False))
        except RuntimeError as e:assert 'EXPLICIT_PAID_APPROVAL' in str(e)
        else:raise AssertionError('Paid opt-in bypassed')
        print('PASS: operational stop file and explicit paid approval')
    finally:restore(tmp,o,p)

def test_cycle_order():
    with tempfile.TemporaryDirectory() as d:
        for n in [1,12,999,1000]:
            q=pathlib.Path(d)/f'CYCLE_{n:03d}'
            q.mkdir();(q/'cycle.json').write_text('{}')
        names=[p.parent.name for p in a.all_cycle_files(d)]
        assert names==['CYCLE_001','CYCLE_012','CYCLE_999','CYCLE_1000']
        print('PASS: no 999-cycle glob truncation')

if __name__=='__main__':
    test_terminal_journal_and_no_rebilling()
    test_stop_and_no_approval()
    test_cycle_order()
    print('AUTONOMOUS_OFFLINE_TESTS_PASS; paid WSL integration NOT YET RUN')
