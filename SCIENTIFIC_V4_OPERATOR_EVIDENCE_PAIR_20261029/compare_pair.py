#!/usr/bin/env python3
"""Read-only comparison of two operator-guided V4 research branches.

Counts/strings are observations of recorded behavior, not certification of
mechanistic novelty or causal effects of evidence on a stochastic researcher.
"""
import argparse, json
from pathlib import Path
from e2core.core import EvolutionJournal

RECEIPT='OPERATOR_CONTROLLED_PAIRED_RESEARCH_BRANCH_20261029'

def inspect(path):
    j=EvolutionJournal(path.expanduser().resolve(strict=True));s=j.verify()
    rows=j._events()
    recs=[e for e in rows if e['kind']=='OPERATIONAL_PAUSE' and e['payload'].get('reason')==RECEIPT]
    assert len(recs)==1,'NOT_AN_EXPECTED_TRIAL_ROOT'
    begin=recs[0]['seq']; newly=[x for x in rows if x['seq']>begin]
    decisions=[x['payload']['id'] for x in newly if x['kind']=='CONTROLLER_DECISION']
    newworks=[w for wid,w in s.work.items() if any(x['kind']=='EVOLUTION_APPLIED' and
         x['payload'].get('work',{}).get('id')==wid for x in newly)]
    newassets=[a for aid,a in s.assets.items() if any(x['kind']=='ASSET_PUBLISHED' and
         x['payload'].get('id')==aid for x in newly)]
    newproblems=[x['payload'] for x in newly if x['kind']=='PROBLEM_CREATED']
    newcalls=[x['payload'].get('id') for x in newly if x['kind']=='MODEL_CALL_INTENT']
    pauses=[x['payload'] for x in newly if x['kind']=='OPERATIONAL_PAUSE']
    reg=[x['payload'].get('id') for x in newly if x['kind']=='SOURCE_REGISTERED']
    return {
      'root':str(j.root),'condition':recs[0]['payload']['condition'],
      'start_at_event_seq':begin,'total_new_events_after_receipt':len(newly),
      'registered_source_ids_after_receipt':reg,
      'new_model_intents':newcalls,
      'new_model_intent_count':len(newcalls),
      'new_controller_decisions':decisions,
      'new_work':[{'id':w['id'],'mode':w['mode'],'operation':w['operation'],
         'asset_input_ids':w.get('asset_input_ids',[]),'question':w.get('question'),
         'status':w['status']} for w in newworks],
      'new_scientific_assets':[{'id':a['id'],'kind':a['kind'],
         'parent_ids':a.get('parent_ids',[]),'source_ids':a.get('source_ids',[]),
         'claim':a.get('claim'),'delta_from_parents':a.get('delta_from_parents'),
         'predictions':a.get('predictions',[]),'limitations':a.get('limitations',[])} for a in newassets],
      'new_problems':newproblems,
      'recent_pauses':pauses[-12:],
      'last_program_status':s.program_reviews[-1]['scientific_status'] if s.program_reviews else None,
      'historical_unknown_count':sum(x['state']=='UNCERTAIN' for x in s.model_calls.values()),
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--control',required=True,type=Path)
    p.add_argument('--evidence',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    a=p.parse_args()
    assert not a.out.exists(),'REFUSE_OVERWRITE'
    c=inspect(a.control);e=inspect(a.evidence)
    assert c['condition']=='CONTROL' and e['condition']=='OPERATOR_EVIDENCE', 'WRONG_BRANCH_CONDITIONS'
    report={'interpretation':'NO_AUTOMATED_SCIENCE_CERTIFICATION_OR_CAUSAL_ATTRIBUTION',
      'only_evidence_branch_got_operator_source':True,
      'control':c,'evidence':e,
      'trial_observation':{'new_work_counts':{'control':len(c['new_work']),'evidence':len(e['new_work'])},
        'new_asset_counts':{'control':len(c['new_scientific_assets']),
                            'evidence':len(e['new_scientific_assets'])},
        'new_controller_counts':{'control':len(c['new_controller_decisions']),
                                 'evidence':len(e['new_controller_decisions'])}},
      'interpretive_cautions':['New agent action alone does not establish scientific progress.',
          'Paper was supplied by an operator, not autonomously discovered in this experiment.',
          'One stochastic paired run is suggestive, not a controlled estimate of causal effect.',
          'Raw source passages can overlap earlier evidence, reducing intervention novelty.',
          'Review unmodified scientific claims, calculations and tool results before a Level II claim.']}
    a.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'saved':str(a.out),**report['trial_observation']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
