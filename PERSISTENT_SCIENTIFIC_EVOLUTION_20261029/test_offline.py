#!/usr/bin/env python3
"""Offline tests of the actual carry/snapshot/lineage/guard logic, no paid calls."""
import hashlib, json, os, pathlib, sys, tempfile
from types import SimpleNamespace

import persistent_population as p

canon=lambda x: json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
sha=lambda x:hashlib.sha256(x).hexdigest()

class FakeJournal:
    store={}
    def __init__(self,root):
        self.root=pathlib.Path(root).resolve()
        if str(self.root) not in self.store:
            self.store[str(self.root)]=SimpleNamespace(program=None,problems={},assets={},sources={},work={},
                program_reviews=[],controller_decisions=[],model_calls={},tool_results={},rows=[])
        self.s=self.store[str(self.root)]
        self.rows=self.s.rows
    def init(self,problem,origin='X',criteria=None):
        self.root.mkdir(parents=True)
        self.s.program={'problem':problem,'criteria':criteria}
        self.s.problems['P0']={'id':'P0','question':problem,'parents':[]}
        self.append('PROGRAM_CREATED',{'problem':problem})
    def append(self,kind,payload):
        row={'kind':kind,'payload':payload,'seq':len(self.rows)+1}
        self.rows.append(row)
        if kind=='PROBLEM_CREATED':self.s.problems[payload['id']]=payload
        elif kind=='HISTORICAL_ASSET_INDEXED':
            assert all(par in self.s.assets for par in payload.get('parent_ids',[]))
            assert all(s in self.s.sources for s in payload['source_ids'])
            self.s.assets[payload['id']]={**payload,'origin':'AUDIT_EXTRACTED_HISTORICAL_AI_NOT_LIVE_WORK'}
        return row
    def add_source(self,ident,kind,record,description):
        assert ident not in self.s.sources
        self.s.sources[ident]={'kind':kind,'blob':self.blob(record),'description':description}
    def blob(self,obj):
        raw=canon(obj);digest=sha(raw)
        folder=self.root/'blobs';folder.mkdir(exist_ok=True)
        (folder/digest).write_bytes(raw)
        return digest
    def raw(self,digest):return (self.root/'blobs'/digest).read_bytes()
    def verify(self):return self.s
    def _events(self):return self.rows

def fake_verify(mods,root):
    j=FakeJournal(root)
    return j,j.verify()

def test_carry():
    with tempfile.TemporaryDirectory(prefix='scientificpop-') as tmp:
        source=pathlib.Path(tmp)/'old'
        j=FakeJournal(source);j.init('EXACT ORIGINAL P0')
        a={'id':'A_old','kind':'HYPOTHESIS','problem_id':'P0','claim':'An A claim',
            'scope':'Assumed', 'assumptions':'Toy', 'parent_ids':[],
            'source_ids':[], 'predictions':['test'], 'limitations':[], 'status':'PROPOSED'}
        b={'id':'A_child','kind':'COUNTEREXAMPLE','problem_id':'P0','claim':'B refutes subcase',
            'scope':'Limited', 'assumptions':'Counterexample', 'parent_ids':['A_old'],
            'source_ids':[], 'predictions':[], 'delta_from_parents':'actual delta',
            'limitations':['restricted'], 'status':'PROPOSED'}
        j.s.assets[a['id']]=a;j.s.assets[b['id']]=b
        j.s.work['W_still_running']={'status':'ACTIVE','operation':'DEVELOP','mode':'INFORMED',
            'question':'Check conditional physical model','published':['A_child']}
        j.s.program_reviews=[{'scientific_status':'ONGOING','rationale':'not solved'}]
        j.add_source('SRC_INHERITED_TOOL_OLD','EXTERNAL_AUDIT',{
            'evidence_class':'OA_FULLTEXT_TEXT',
            'original_returned_data':{'result':{'text':'source excerpt'}},
            'original_root':'/original/execution',
            'original_tool_id':'T_original',
            'original_tool_source_id':'SRC_old'},'Earlier real tool record, not re-executed')
        mods=SimpleNamespace(J=FakeJournal,sha=sha,canon=canon)
        old_transfer=p.pop.record_direct_tool_sources
        try:
            p.pop.record_direct_tool_sources=lambda *args,**kwargs:{'registered_direct_sources':0,'ids':[]}
            target=pathlib.Path(tmp)/'NEW'
            result=p.prepare_clean_portfolio(mods,source,target)
        finally:p.pop.record_direct_tool_sources=old_transfer
        assert result['source_assets']==2
        new=FakeJournal(target)
        # Root name changes from staging to final, so fake state is separately
        # tracked; inspect canonical persisted receipt as the physical artifact.
        rec=json.loads((target/'carry_receipt.json').read_text())
        assert len(rec['edges'])==2
        assert rec['edges'][1]['upstream_parents']==['A_old']
        assert rec['edges'][1]['current_parents']==[rec['edges'][0]['current_id']]
        assert rec['unfinished_work_statuses_preserved_as_history'] is True
        assert len(rec['previously_registered_external_sources_carried'])==1
        assert rec['previously_registered_external_sources_carried'][0]['prior_id']=='SRC_INHERITED_TOOL_OLD'
        assert not (target/'events'/'FORGED_WORK_COMPLETION').exists()
        assert FakeJournal(source).verify().work['W_still_running']['status']=='ACTIVE'
        # No source must be overwritten on a second call.
        try:p.prepare_clean_portfolio(mods,source,target)
        except RuntimeError as exc: assert 'ALREADY_EXISTS' in str(exc)
        else:raise AssertionError('Carry overwrote a prior generation')
        print('PASS: complete parent translation, original active work status, no overwrite')

def test_compat_import():
    import population_resume as compat
    a={'id':'A_any','claim':'Model claim','scope':'scope','assumptions':'x'}
    record={'kind':'PEER_RESEARCH_RESULT_HISTORICAL_AI_NOT_NEW_EXECUTION',
        'verification':'SAVED_WORKER_MODEL_CALL_AND_ORIGIN_STEP_MATCHED',
        'not_primary_literature':True,'original_asset':a,
        'original_asset_sha256':sha(canon(a)),'original_asset_id':'A_any',
        'original_root':'/original/peer'}
    mods=SimpleNamespace(sha=sha,canon=canon)
    c=compat.peer_science_record(mods,'SRC_PEER_ASSET_TEST',record)
    assert c['ref']=='/original/peer#A_any'
    assert c['science_sha256']==sha(canon(a))
    try:compat.peer_science_record(mods,'SRC_PEER_ASSET_TEST',dict(record,original_asset_sha256='0'*64))
    except RuntimeError as exc:assert 'DIGEST' in str(exc)
    else:raise AssertionError('Did not reject tampered source')
    print('PASS: peer historical input compatibility with hash validation')

def test_execution_safeguard():
    args=SimpleNamespace(paid=False)
    try:p.run(args)
    except RuntimeError as exc:assert 'EXPLICIT' in str(exc)
    else:raise AssertionError('Ran without explicit paid approval')
    assert p.TERMINAL=={'HOLD_WITH_RATIONALE','SCOPED_NEGATIVE','REVIEW_WORTHY_CANDIDATE'}
    print('PASS: paid guard and science/operational terminal distinction')

if __name__=='__main__':
    test_carry();test_compat_import();test_execution_safeguard()
    print('OFFLINE_TESTS_PASS; actual WSL runtime end-to-end test NOT run')
