#!/usr/bin/env python3
"""Read-only operational schema failure -> quarantine -> population receipt tests.

Does not use network/API or touch a real Journal. Ensures failed work is NOT
converted to a scientific decision or new live science artifact.
"""
import json
from pathlib import Path
from types import SimpleNamespace
import autonomous_population as a
import persistent_population as pp
from test_autonomous_offline import Journal,setup,restore,sha,canon


def test_real_saved_rejections_preserved():
    temp,root,old,provider=setup()
    try:
        mods=a.pop.gen.modules()
        cycle_root=root/'CYCLE_000'
        cycle_root.mkdir()
        base=Journal(cycle_root/'BASE');base.init('Exact scientific problem P0')
        peer=Journal(cycle_root/'SYN_02');peer.init('Exact scientific problem P0')
        for i in range(1,6):
            cid=f'CTRL_D0000{i}'
            peer.append('MODEL_CALL_INTENT',{'id':cid,'actor':'CONTROLLER',
                'request_blob':peer.blob({'request':i})})
            response=peer.blob({'choices':[{'message':{'content':json.dumps({'actions':[]})}}]})
            peer.append('MODEL_CALL_SAVED',{'id':cid,'response_blob':response})
            reason=('CONTROLLER_PLAN_REJECTED:E3R1_DUPLICATE_OR_UNKNOWN_WORK'
                   if i%2 else 'CONTROLLER_PLAN_REJECTED:E3R1_ONGOING_NO_RUNNABLE_OR_NEW_WORK_AFTER_PORTFOLIO')
            peer.append('OPERATIONAL_PAUSE',{'reason':reason,'call_id':cid})
        good=Journal(cycle_root/'SYN_01');good.init('Exact scientific problem P0')
        cycle={'index':0,'stage':'PEERS','base':str(base.root),
            'peers':{'SYN_01':str(good.root),'SYN_02':str(peer.root)},
            'population_root':str(cycle_root/'POPULATION')}
        assert a.schema_quarantines(mods,root,cycle)=={}
        result=a.quarantine_peer_schema(mods,root,cycle,'SYN_02','SCHEMA_RECOVERY_ATTEMPTS_EXHAUSTED')
        assert result['status']=='SCHEMA_EXHAUSTED_PEER_QUARANTINED_NO_PAID'
        assert result['rejected_controller_attempts']==5
        assert a.quarantine_peer_schema(mods,root,cycle,'SYN_02','SCHEMA_RECOVERY_ATTEMPTS_EXHAUSTED')['status'].startswith('ALREADY_')
        receipts=a.schema_quarantines(mods,root,cycle)
        assert set(receipts)=={'SYN_02'}
        out=Journal(cycle_root/'STAGE');out.init('Exact scientific problem P0')
        report=pp._import_quarantined_peer(mods,out,base.verify(),'SYN_02',str(peer.root),receipts['SYN_02'])
        assert report['decisions']==0 and report['new_assets_imported']==0
        src=out.verify().sources['SRC_PEER_DECISION_SYN_02']
        body=json.loads(out.raw(src['blob']))
        assert body['decisions']==[] and body['new_assets']==[]
        assert body['operationally_blocked_not_a_scientific_hold']
        assert len(body['saved_controller_rejections'])==5
        assert peer.verify().controller_decisions==[]
        assert len(peer.verify().model_calls)==5
        assert not peer.verify().work and not out.verify().assets
        # A previously saved, legitimate SYN_01 YIELD plus schema-quarantined
        # SYN_02 must advance to COMBINE without running another paid segment.
        meta=Journal(root/'AUTONOMOUS_META')
        cid='CALL_M_HEALTHY_YIELD'
        meta.append('MODEL_CALL_INTENT',{'id':cid,'actor':'CONTROLLER',
            'request_blob':meta.blob({'messages':[{}, {'content':json.dumps({
                'stage':'PEER','cycle_number':0,'peer_name':'SYN_01'})}]})})
        meta.append('MODEL_CALL_SAVED',{'id':cid,'response_blob':meta.blob({'choices':[{'message':{
            'content':'{"decision":"YIELD_TO_POPULATION","rationale":"Done"}'}}]})})
        meta.append('CONTROLLER_DECISION',{'id':'M_HEALTHY_YIELD','call_id':cid,
            'parsed_blob':meta.blob({'decision':'YIELD_TO_POPULATION','rationale':'Done'})})
        orig_cycle=a.current_cycle;orig_update=a.pp.update_cycle
        try:
            a.current_cycle=lambda exp:cycle
            a.pp.update_cycle=lambda exp,c:None
            result=a.step_once(mods,root,SimpleNamespace(bootstrap_peers=2))
            assert result=='CONTINUE' and cycle['stage']=='COMBINE'
        finally:
            a.current_cycle=orig_cycle;a.pp.update_cycle=orig_update
        print('PASS: recovered cycle advances to COMBINE with zero paid calls')
        assert len(peer.verify().model_calls)==5
        assert not peer.verify().work and not out.verify().assets
        print('PASS: 5 rejected saved plans quarantined, no new paid calls or fabricated science')
        # Mutating the donor Journal after quarantine must fail closed.
        peer.append('OPERATIONAL_PAUSE',{'reason':'FOLLOWUP_SHOULD_NOT_HAVE_RUN'})
        try:a.schema_quarantines(mods,root,cycle)
        except RuntimeError as e:assert 'DRIFT_OR_TAMPER' in str(e)
        else:raise AssertionError('Quarantine missed donor mutation')
        print('PASS: donor mutation after quarantine fails closed')
    finally:restore(temp,old,provider)

if __name__=='__main__':
    test_real_saved_rejections_preserved()
    print('SCHEMA_QUARANTINE_OFFLINE_TESTS_PASS; live WSL integration NOT RUN')
