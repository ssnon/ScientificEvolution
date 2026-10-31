#!/usr/bin/env python3
"""No actual Journal/model access; verifies only runtime shape conversion and FRESH passthrough."""
import copy, hashlib, json, sys, types
from pathlib import Path
from types import SimpleNamespace
import population_resume as r

def canon(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
def sha(b):return hashlib.sha256(b).hexdigest()
a={'id':'A_old','kind':'HYPOTHESIS','claim':'Physical hypothesis, unverified',
   'scope':'conditional','assumptions':'none proven','parent_ids':[],'predictions':['P1'],
   'limitations':['model output']}
d={'kind':'PEER_RESEARCH_RESULT_HISTORICAL_AI_NOT_NEW_EXECUTION',
   'verification':'SAVED_WORKER_MODEL_CALL_AND_ORIGIN_STEP_MATCHED',
   'not_primary_literature':True,'original_asset':a,
   'original_asset_id':'A_old','original_root':'/original/root',
   'original_asset_sha256':sha(canon(a)),
   'original_model_call_id':'WK_W_00001',
   'original_model_response_sha256':'a'*64}
m=SimpleNamespace(sha=sha,canon=canon)
converted=r.peer_science_record(m,'SRC_PEER_ASSET_good',d)
assert converted['ref']=='/original/root#A_old'
assert converted['science']['original_asset']==a
assert converted['tool_status']=='NO_NEW_TOOL_EXECUTION'
for mutate in [lambda q:q.update(original_asset_sha256='f'*64),lambda q:q.update(not_primary_literature=False)]:
    bad=copy.deepcopy(d);mutate(bad)
    try:r.peer_science_record(m,'SRC_PEER_ASSET_bad',bad)
    except RuntimeError:pass
    else:raise AssertionError('bad peer source accepted')

sid='SRC_PEER_ASSET_good'
blob='a'*64
legacy_sid='SRC_ISO_old'
legacy_blob='b'*64
legacy={'ref':'/old/#asset','science':{'scientific_work':'Earlier independent AI'},
        'science_sha256':'c'*64,'tool_result':{'status':'NOT_CERTIFIED_BY_IMPORT'}}
sources={sid:{'kind':'HISTORICAL_AI','blob':blob},
         legacy_sid:{'kind':'HISTORICAL_AI','blob':legacy_blob}}
assets={'A_PEER_child':{'source_ids':[sid],'source_ref':converted['ref']},
        'A_ISO_old':{'source_ids':[legacy_sid],'source_ref':legacy['ref']}}
state=SimpleNamespace(sources=sources,work={
  'W_INFORMED':{'mode':'INFORMED','source_ids':[],'asset_input_ids':list(assets),'steps':[]},
  'W_FRESH':{'mode':'FRESH','source_ids':[],'asset_input_ids':[],'steps':[]}})
class J:
    root=Path('/tmp/fake_new_population')
    def verify(self):return state
    def raw(self,hashval):return canon({blob:d,legacy_blob:legacy}[hashval])
    def input_for(self,wid):
        return {'parent_assets':[assets[x] for x in state.work[wid]['asset_input_ids']], 'source_entries':[]}
prior=lambda j,wid,tool_capabilities=None: {'original':True,'wid':wid}
# Mock the read-only ancillary module, never use an installed package.
rootmod=types.ModuleType('e2core')
ctxmod=types.ModuleType('e2core.research_context')
ctxmod.research_worker_context=lambda j,wid,tool_capabilities=None:{'id':wid}
sys.modules.setdefault('e2core',rootmod)
sys.modules['e2core.research_context']=ctxmod
spe=SimpleNamespace(_ORIGINAL_WORKER_INPUT=prior)
mods=SimpleNamespace(spe=spe,sha=sha,canon=canon)
j=J()
with r.historical_input_compat(mods,j.root):
    assert spe._ORIGINAL_WORKER_INPUT(j,'W_FRESH') == prior(j,'W_FRESH')
    x=spe._ORIGINAL_WORKER_INPUT(j,'W_INFORMED')
    assert x['pinned_input']['authorized_historical_records'][0]['ref']=='/old/#asset'
    assert x['pinned_input']['authorized_historical_records'][1]['ref']=='/original/root#A_old'
    assert x['research_capability_state']=={'id':'W_INFORMED'}
assert spe._ORIGINAL_WORKER_INPUT is prior
assert not hasattr(j,'append')
print('PASS: peer provenance, raw digest, malformed source fail-closed, FRESH unchanged, legacy G0 preserved, restored runtime hook')
