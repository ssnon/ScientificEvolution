#!/usr/bin/env python3
"""Read-only, no-provider diagnostic of the actual pending controller model wire.

Requires original V1.4 Memory + Frontier + AUT + runtime on PYTHONPATH.
Reads only the active experiment Journal. Does not patch Journal, allocate new model
calls, replay incompatible responses or weaken DurableModel's hash guard.
"""
from __future__ import annotations
import argparse
import difflib
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import memory_bridge as mm


def canon(o):
    return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()

def sha(raw):
    return hashlib.sha256(raw).hexdigest()



def _hash_text(x):
    return hashlib.sha256(str(x).encode('utf8')).hexdigest() if x is not None else None


def _diff_prompt(a,b):
    a_lines=a.splitlines() if isinstance(a,str) else []
    b_lines=b.splitlines() if isinstance(b,str) else []
    edits=[]
    matcher=difflib.SequenceMatcher(a=a_lines,b=b_lines,autojunk=False)
    for op,i,j,k,l in matcher.get_opcodes():
        if op=='equal':continue
        edits.append({'change':op,'archived_lines':[i+1,j],'current_lines':[k+1,l],
                      'archived_excerpt':' '.join(a_lines[i:j])[:160],
                      'current_excerpt':' '.join(b_lines[k:l])[:160]})
        if len(edits)==5:break
    return edits


def compare_call(record,archived_wire,actor,work_id,system,payload,model,max_tokens):
    """Pure diagnostic: NEVER authorizes archived replay."""
    message=archived_wire.get('messages') or []
    old_system=(message[0].get('content') if len(message)>0 and isinstance(message[0],dict) else None)
    old_user=(message[1].get('content') if len(message)>1 and isinstance(message[1],dict) else None)
    try:old_payload=json.loads(old_user)
    except (TypeError,ValueError):old_payload=None
    matches={
        'actor':record.get('actor')==actor,
        'work_id':record.get('work_id')==work_id,
        'model':archived_wire.get('model')==model,
        'max_tokens':archived_wire.get('max_tokens')==max_tokens,
        'temperature':archived_wire.get('temperature')==0.7,
        'response_format':archived_wire.get('response_format')=={'type':'json_object'},
        'system_prompt':old_system==system,
    }
    receipt=(old_payload.get('science_memory_request_receipt') if isinstance(old_payload,dict) else None)
    original_sha=receipt.get('original_payload_sha256') if isinstance(receipt,dict) else None
    prior_version=receipt.get('version') if isinstance(receipt,dict) else None
    normalized,fields=mm.normalized_provenance_version_candidate(payload,prior_version)
    current_sha=mm._digest(payload)
    norm_sha=mm._digest(normalized) if normalized is not None else None
    current_wire={'model':model,'temperature':0.7,'max_tokens':max_tokens,
                  'response_format':{'type':'json_object'},
                  'messages':[{'role':'system','content':system},
                              {'role':'user','content':json.dumps(payload,ensure_ascii=False,sort_keys=True,allow_nan=False)}]}
    raw_key_diff=[]
    if isinstance(old_payload,dict) and isinstance(payload,dict):
        raw_key_diff=sorted(k for k in old_payload.keys()|payload.keys()
                            if old_payload.get(k)!=payload.get(k))
    # Saved compressed view is not directly comparable with raw current source.
    return {
        'call_id':record.get('id'),
        'contract_field_matches':matches,
        'mismatched_contract_fields':[k for k,v in matches.items() if not v],
        'archived_model':archived_wire.get('model'),
        'current_model':model,
        'archived_max_tokens':archived_wire.get('max_tokens'),
        'current_max_tokens':max_tokens,
        'archived_system_sha256':_hash_text(old_system),
        'current_system_sha256':_hash_text(system),
        'archived_system_length':len(old_system) if isinstance(old_system,str) else None,
        'current_system_length':len(system) if isinstance(system,str) else None,
        'prompt_only_trailing_whitespace_diff':(old_system!=system and isinstance(old_system,str)
                                                  and isinstance(system,str) and old_system.rstrip()==system.rstrip()),
        'prompt_changed_line_previews':_diff_prompt(old_system,system),
        'saved_request_wire_sha256':record.get('request_blob'),
        'current_uncompacted_wire_sha256':sha(canon(current_wire)),
        'archived_memory_receipt_version':prior_version,
        'archived_precompaction_sha256':original_sha,
        'current_precompaction_sha256':current_sha,
        'normalized_metadata_sha256':norm_sha,
        'only_normalized_metadata_matches_archived_precompaction':(normalized is not None and norm_sha==original_sha),
        'raw_science_input_matches_archived_precompaction':original_sha==current_sha,
        'normalized_fields':fields,
        'archived_compacted_view_vs_current_raw_changed_top_keys':raw_key_diff[:70],
        'archived_compacted_view_is_not_directly_comparable_to_current_raw':True,
        'safe_to_replay':False,
        'not_an_authorization_to_ignore_contract_mismatch':True,
    }



def run(experiment,model_name,max_tokens):
    import autonomous_population as aut
    import population_run as pop
    import frontier_runtime as fr
    import pending_replay_probe as prior_probe

    class DiagnosticModel(prior_probe.ProbeModel):
        def call(self,ident,actor,work_id,system,payload):
            rec=self.j.verify().model_calls.get(ident)
            if ident.startswith('OPP_') and rec is not None:
                archived_wire=json.loads(self.j.raw(rec['request_blob']))
                data=compare_call({**rec,'id':ident},archived_wire,actor,work_id,system,
                                  payload,self.model,self.max_tokens)
                raise prior_probe.StopProbe({'status':'READ_ONLY_OPP_CONTRACT_DIFF',
                        'diagnostic':data,'prior_saved_replays':self.history,
                        'zero_provider_requests_sent':True})
            return super().call(ident,actor,work_id,system,payload)

    root=Path(experiment).expanduser().resolve()
    mods=pop.gen.modules()
    cycle,cp=__import__('evolution_frontier')._current_root(root)
    j=mods.J(cp)
    rows=j._events();head=sha(canon(rows[-1]));size=len(rows)
    s=j.verify()
    if any(v.get('state')!='SAVED' for v in s.model_calls.values()):
        return {'status':'UNRESOLVED_MODEL_CALL','zero_provider_requests_sent':True}
    import e2core.engine as engine
    proxy=prior_probe.ReadonlyJournal(j)
    fake=DiagnosticModel(proxy,model_name,max_tokens)
    ctl=SimpleNamespace(j=proxy,model=fake,_native_tool_contract=True)
    ident=engine.Engine._next_controller_id(ctl)
    with fr.activate(mods,aut),mm.activate(mods):
        try:
            outcome=mods.v3.controller_v3(ctl,ident)
            info={'status':'CONTROLLER_RETURNED_WITHOUT_NEW_CALL','outcome':outcome}
        except prior_probe.StopProbe as exc:
            info=exc.record
        except Exception as exc:
            info={'status':'UNEXPECTED_DIAGNOSTIC_ERROR','error_type':type(exc).__name__,
                  'detail':str(exc)}
    fresh=j._events()
    if len(fresh)!=size or sha(canon(fresh[-1]))!=head:
        raise RuntimeError('READONLY_DIAGNOSTIC_MUTATED_JOURNAL')
    return {'generation':cycle['index'],'journal_root':str(cp),
            'controller_attempt_id':ident,'original_journal_head_sha256':head,
            'original_event_count':size,'journal_unchanged':True,
            'provider_requests_sent':0,**info}

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--experiment',required=True)
    ap.add_argument('--model',default='openai/gpt-5.6-luna')
    ap.add_argument('--max-tokens',type=int,default=16000)
    a=ap.parse_args()
    try:r=run(a.experiment,a.model,a.max_tokens)
    except Exception as exc:r={'status':'DIAGNOSTIC_SETUP_ERROR','error_type':type(exc).__name__,
                               'detail':str(exc),'provider_requests_sent':0}
    print(json.dumps(r,ensure_ascii=False,indent=2,default=str))
    sys.exit(0 if r['status']=='READ_ONLY_OPP_CONTRACT_DIFF' else 3)
