#!/usr/bin/env python3
"""Read-only, zero-provider dry-run of exact next Controller opportunity request.

Unlike historical Preflight this constructs the next D00008 payload under the
actual V4 / Population scoped runtime then tests the current attention gate.
No model adapter capable of network access is constructed and the original E2
Journal is read-only guarded by safe_resume_probe.ReadonlyJournal.
"""
from __future__ import annotations
import argparse,json,sys
import safe_resume_probe as sr
from pending_replay_probe import ProbeModel,StopProbe
import memory_bridge as mm

class AttentionProbeModel(ProbeModel):
    def call(self,ident,actor,work_id,system,payload):
        if ident in self.j.verify().model_calls:
            return super().call(ident,actor,work_id,system,payload)
        before={k:mm.jsize(v) for k,v in payload.items()} if isinstance(payload,dict) else {}
        summary={'next_call_id':ident,'actor':actor,'original_input_chars':mm.jsize(payload),
            'largest_input_fields':sorted(before.items(),key=lambda x:-x[1])[:24],
            'budget_chars':mm.BUDGETS['all_controller'],
            'previous_saved_calls_replayed':list(self.history),
            'provider_requests_sent':0,'journal_unchanged':True}
        if not (ident.startswith(('OPP_','CTRL_')) and actor=='CONTROLLER'):
            raise StopProbe({'status':'NEW_NON_ADVISOR_CALL_NO_PAID',**summary})
        try:
            bound=mm.bound_advisor_payload(payload,ident)
        except Exception as exc:
            raise StopProbe({'status':'NEXT_ATTENTION_BLOCKED_NO_PAID',**summary,
                'error_type':type(exc).__name__,'reason':str(exc)}) from exc
        checked={k:mm.jsize(v) for k,v in bound.items()}
        orig_problem_ids=[x['id'] for x in payload.get('problems',[]) if isinstance(x,dict) and 'id' in x]
        new_problem_ids=[x['id'] for x in bound.get('problems',[]) if isinstance(x,dict) and 'id' in x]
        original_claim_refs=[(x.get('asset_id'),x.get('relation'),tuple(x.get('evidence_ids',[])))
            for x in payload.get('claim_prior_art_assessment',{}).get('claim_assessments',[])]
        new_claim_refs=[(x.get('asset_id'),x.get('relation'),tuple(x.get('evidence_ids',[])))
            for x in bound.get('claim_prior_art_assessment',{}).get('claim_assessments',[])]
        original_impact_refs=[(x.get('asset_id'),x.get('relation_to_p0'),tuple(x.get('evidence_ids',[])))
            for x in payload.get('problem_level_impact',{}).get('claim_to_problem',[])]
        new_impact_refs=[(x.get('asset_id'),x.get('relation_to_p0'),tuple(x.get('evidence_ids',[])))
            for x in bound.get('problem_level_impact',{}).get('claim_to_problem',[])]
        checks={'problem_ids_all_preserved':orig_problem_ids==new_problem_ids,
                'claim_reference_ledger_preserved':original_claim_refs==new_claim_refs,
                'impact_reference_ledger_preserved':original_impact_refs==new_impact_refs,
                'active_work_unchanged':payload.get('v3_science_work_options',{}).get('active_scientific_work')==
                                        bound.get('v3_science_work_options',{}).get('active_scientific_work'),
                'P0_unmodified':payload.get('program')==bound.get('program'),
                'original_payload_sha_preserved':bound['science_memory_request_receipt']['original_payload_sha256']==mm._digest(payload),
                'bounded_below_limit':mm.jsize(bound)<=mm.BUDGETS['all_controller']}
        safe=all(checks.values())
        raise StopProbe({'status':'NEXT_ATTENTION_READY_NO_PAID' if safe else 'NEXT_ATTENTION_INTEGRITY_BLOCKED',
            **summary,'bounded_input_chars':mm.jsize(bound),'largest_bounded_fields':
            sorted(checked.items(),key=lambda x:-x[1])[:24],
            'integrity':checks,'model_request_created':False,
            'scientific_changes':False})

def check(experiment,model,max_tokens):
    old=sr.ProbeModel
    sr.ProbeModel=AttentionProbeModel
    try:
        result=sr.probe(experiment,model,max_tokens)
    finally:
        sr.ProbeModel=old
    # Original source guards are included in sr.probe's result. It alone
    # serializes via readonly Journal and never creates DurableModel.
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--experiment',required=True)
    p.add_argument('--model',default='openai/gpt-5.6-luna')
    p.add_argument('--max-tokens',type=int,default=16000)
    a=p.parse_args()
    try:result=check(a.experiment,a.model,a.max_tokens)
    except Exception as exc:result={'status':'ATTENTION_PROBE_SETUP_ERROR','error_type':type(exc).__name__,
                                    'reason':str(exc),'provider_requests_sent':0}
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
    sys.exit(0 if result.get('status')=='NEXT_ATTENTION_READY_NO_PAID' else 3)
