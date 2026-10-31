#!/usr/bin/env python3
"""Prepare a fair V4 Control/Evidence pair using append-only immutable branches.

Requires the user's pinned, working V4 repository on PYTHONPATH. Original ROOT
is read-locked, never edited. No model calls. Only previously audited historical
UNKNOWN is allowed, and never reissued. Do NOT use on a currently running ROOT.
"""
import argparse, hashlib, json, shutil, tempfile
from pathlib import Path
from e2core.core import EvolutionJournal, canon, sha, guard
import scientific_closed_loop_v3 as v3
import scientific_research_readiness_v4 as v4
import scientific_problem_evolution as spe
import scientific_v4_clean_baseline as baseline

RECEIPT='OPERATOR_CONTROLLED_PAIRED_RESEARCH_BRANCH_20261029'
EXPECTED_D='D00078'
EXPECTED_EVENTS=1870

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source-root',required=True,type=Path)
    p.add_argument('--packet',required=True,type=Path)
    p.add_argument('--out-parent',required=True,type=Path)
    args=p.parse_args()
    source=args.source_root.expanduser().resolve(strict=True)
    parent=args.out_parent.expanduser().resolve(strict=True)
    guard(parent.is_dir() and not parent.is_relative_to(source),'INVALID_OUT_DIRECTORY')
    dests={k:parent/('V4_D78_'+k+'_20261029') for k in ('CONTROL','OPERATOR_EVIDENCE')}
    guard(all(not x.exists() for x in dests.values()),'DESTINATION_ALREADY_EXISTS')
    assert args.packet.is_file(),'PACKET_MISSING'
    packet_bytes=args.packet.read_bytes()
    records=spe.validate_packet(json.loads(packet_bytes))
    guard(all(x['origin_url_or_doi'].endswith('/PMC4129422/fullTextXML') for x in records),
          'UNEXPECTED_EXPERIMENTAL_SOURCE')
    guard(len(records)==7, 'EXPECTED_SEVEN_AUDITED_TEXT_WINDOWS')
    v3.source_code_guard();baseline.source_code_guard()

    with baseline.source_read_lock(source):
        base=EvolutionJournal(source);st=base.verify();events=base._events()
        guard(len(events)==EXPECTED_EVENTS,'SOURCE_EVENT_COUNT_CHANGED_REAUDIT')
        guard(st.controller_decisions[-1]['id']==EXPECTED_D,'CONTROLLER_STATE_CHANGED_REAUDIT')
        v4.inspect(source)
        receipt=v3._recovery_receipt(base)
        unresolved={cid for cid,c in st.model_calls.items() if c['state']!='SAVED'}
        guard(unresolved=={receipt['original_call_id']} and
              st.model_calls[receipt['original_call_id']]['state']=='UNCERTAIN',
              'UNREVIEWED_PENDING_OR_UNKNOWN_MODEL_CALL')
        guard(not any(sid.startswith('SRC_PRIOR_PMC4129422_') for sid in st.sources),
              'ALREADY_HAS_OPERATOR_PAPER_EVIDENCE')
        src_head=sha(canon(events[-1])); p0=st.program['problem']
        stages={}
        committed=[]
        try:
            for condition in dests:
                stage=Path(tempfile.mkdtemp(prefix='.paired-'+condition+'-',dir=parent))
                shutil.rmtree(stage)
                shutil.copytree(source,stage,symlinks=False)
                stages[condition]=stage
                j=EvolutionJournal(stage)
                assert sha(canon(j._events()[-1]))==src_head,'COPIED_SOURCE_DIFFERS'
                assert j.verify().program['problem']==p0,'ORIGINAL_PROBLEM_CHANGED'
                j.append('OPERATIONAL_PAUSE',{
                    'reason':RECEIPT,'experiment':'OPERATOR_GUIDED_EVIDENCE_UPDATE',
                    'condition':condition,'origin':'OPERATOR_DIRECTED_NOT_AI_DISCOVERED',
                    'source_root':str(source),'source_head_sha256':src_head,
                    'source_event_count':len(events),'source_controller':EXPECTED_D,
                    'history_kept_intact':True,'historical_uncertain_preserved':True,
                    'no_model_call_or_hypothesis_asserted':True,
                    'operator_packet_sha256':hashlib.sha256(packet_bytes).hexdigest() if condition=='OPERATOR_EVIDENCE' else None})
                if condition=='OPERATOR_EVIDENCE':
                    for record in records:
                        sid='SRC_PRIOR_'+record['id']
                        guard(sid not in j.verify().sources,'EVIDENCE_ID_COLLISION')
                        j.add_source(sid,'EXTERNAL_AUDIT',{
                            'kind':'OPERATOR_SUBMITTED_LITERATURE_EXCERPT_NOT_INDEPENDENTLY_VERIFIED',
                            'record':record,'packet_sha256':sha(packet_bytes),
                            'original_file_name':args.packet.name,
                            'selection_origin':'OPERATOR_DIRECTED',
                            'retrieval_execution':'USER_EXECUTED_SCRIPT',
                            'autonomous_discovery_claimed':False,
                        },'Operator-supplied public-paper excerpt, NOT AI autonomous discovery or empirical certification')
                post=j.verify()
                assert post.program['problem']==p0,'P0_MODIFIED'
                assert len(post.controller_decisions)==len(st.controller_decisions),'INVENTED_DECISION'
                assert len(post.model_calls)==len(st.model_calls),'INVENTED_MODEL_CALL'
                assert set(post.assets)==set(st.assets),'INVENTED_ASSET'
                assert v3._recovery_receipt(j)['original_call_id']==receipt['original_call_id'], 'UNKNOWN_OUTCOME_LOST'
                v4.inspect(stage)
            fresh=[wid for wid,w in st.work.items() if w['mode']=='FRESH' and w['status'] in ('ACTIVE','QUEUED')]
            for wid in fresh:
                ci=v4.worker_input(EvolutionJournal(stages['CONTROL']),wid,'NATIVE_RESEARCH_TOOLS')
                ei=v4.worker_input(EvolutionJournal(stages['OPERATOR_EVIDENCE']),wid,'NATIVE_RESEARCH_TOOLS')
                guard(canon(ci)==canon(ei),'FRESH_INPUT_CHANGED_BY_OPERATOR_EVIDENCE:'+wid)
                guard(b'SRC_PRIOR_PMC4129422' not in canon(ei),'OPERATOR_PRIOR_ART_LEAKED_TO_FRESH')
            guard(sha(canon(base._events()[-1]))==src_head,'ORIGINAL_SOURCE_CHANGED_DURING_BRANCHING')
            for condition,path in dests.items():
                stages[condition].rename(path)
                committed.append(path)
            stages.clear()
        except BaseException:
            # Fail closed if only one of the paired outputs was moved.
            for path in committed:
                if path.exists():shutil.rmtree(path)
            raise
        finally:
            for stage in stages.values():
                if stage.exists():shutil.rmtree(stage)
        print(json.dumps({'status':'PAIRED_BRANCHES_CREATED_NO_PAID','source_root':str(source),
          'source_head_sha256':src_head,'source_last_controller':EXPECTED_D,
          'branch_paths':{k:str(x) for k,x in dests.items()},'fresh_input_equal':True,
          'operator_evidence_entries':len(records),'historical_unknown_preserved':True,
          'science_certified':False},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
