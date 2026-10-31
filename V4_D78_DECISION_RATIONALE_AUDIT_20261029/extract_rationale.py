#!/usr/bin/env python3
"""Read-only export of exact model-authored opportunity & Controller rationales.

Never calls a provider, modifies a Journal, or assigns scientific credit.
Use on two already-completed matched-probe roots.
"""
from __future__ import annotations
import argparse, json, pathlib, hashlib
from e2core.core import EvolutionJournal, sha, canon, guard
from e2core.provider import content_from_wire, strict_envelope


def extract(root, decision):
    j=EvolutionJournal(pathlib.Path(root).expanduser().resolve(strict=True))
    s=j.verify()
    d=next((x for x in s.controller_decisions if x['id']==decision),None)
    guard(d is not None, 'DECISION_NOT_FOUND:'+decision)
    def call(cid):
        rec=s.model_calls.get(cid)
        if rec is None:
            return {'call_id':cid, 'status':'NOT_FOUND'}
        data={'call_id':cid,'state':rec['state'],'actor':rec['actor'],
              'request_blob':rec.get('request_blob'),'response_blob':rec.get('response_blob'),
              'model':rec.get('model'),'billing_mode':rec.get('billing_mode')}
        if rec['state']=='SAVED':
            text=content_from_wire(j.raw(rec['response_blob']))
            obj=strict_envelope(text)
            data['response_parsed']=obj
            data['raw_text_when_parse_failed']=text if obj is None else None
        return data
    ctrl=call(d['call_id'])
    req=json.loads(j.raw(s.model_calls[d['call_id']]['request_blob']))
    context=json.loads(req['messages'][1]['content'])
    opp=call('OPP_'+decision)
    provenance=context.get('feedback_call_provenance') or {}
    nvt=call(provenance.get('novelty_model_call',''))
    pmi=call(provenance.get('problem_impact_model_call',''))
    plan=ctrl.get('response_parsed') or {}
    record={
        'root':str(j.root),'decision_id':decision,
        'head_event_sha256':sha(canon(j._events()[-1])),
        'read_only':True,'not_a_science_certification':True,
        'journal_status':{
            'events':len(j._events()),'assets':len(s.assets),
            'controller_decisions':len(s.controller_decisions),
            'open_works':[{'id':w['id'],'mode':w['mode'],'status':w['status'],'question':w.get('question')}
                for w in s.work.values() if w['status'] in ('ACTIVE','QUEUED','DEFERRED')],
        },
        'controller':ctrl,
        'opportunity_assessment':opp,
        'novelty_advisor':nvt,
        'problem_impact_advisor':pmi,
        'controller_context_selected':{
            'prior_art_delta':context.get('prior_art_delta'),
            'problem_impact_delta':context.get('problem_impact_delta'),
            'v3_science_work_options':context.get('v3_science_work_options'),
            'v4_scientific_delta_handoff':context.get('v4_scientific_delta_handoff'),
            'independent_opportunity_assessment':context.get('independent_opportunity_assessment'),
            'portfolio_context':context.get('portfolio_context'),
        },
        'decision_only':{
            'rationale':plan.get('rationale'), 'disposition':plan.get('disposition'),
            'new_problems':plan.get('new_problems',[]),
            'actions':plan.get('actions',[]),
            'portfolio_decisions':plan.get('portfolio_decisions',[]),
            'unresolved_opportunities':plan.get('unresolved_opportunities',[]),
            'objective_assessment':plan.get('objective_assessment'),
        }
    }
    return record


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--control',required=True)
    p.add_argument('--evidence',required=True)
    p.add_argument('--decision-id',default='D00079')
    p.add_argument('--out',type=pathlib.Path,required=True)
    a=p.parse_args()
    guard(not a.out.exists() and a.out.parent.is_dir(),'OUTPUT_ALREADY_EXISTS_OR_BAD_PARENT')
    c=extract(a.control,a.decision_id)
    e=extract(a.evidence,a.decision_id)
    assert c['decision_id']==e['decision_id']
    result={'experiment':'READ_ONLY_EXACT_MATCHED_CONTROLLER_AND_OPPORTUNITY_REASONING',
            'decision_id':a.decision_id,'science_certification':False,
            'control':c,'operator_evidence':e}
    a.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'status':'SAVED_READ_ONLY','file':str(a.out),
       'bytes':a.out.stat().st_size,'control_actions':len(c['decision_only']['actions']),
       'evidence_actions':len(e['decision_only']['actions'])},ensure_ascii=False))

if __name__=='__main__':main()
