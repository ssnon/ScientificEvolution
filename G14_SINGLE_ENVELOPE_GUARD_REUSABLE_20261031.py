#!/usr/bin/env python3
"""G14 runtime-only single-JSON-envelope guard, science/provenance fail-closed.

Background: two G14 workers were blocked because the model emitted two complete JSON
objects separated by whitespace; finish_reason was 'stop', not token exhaustion.

This wrapper:
  * never reinterprets/reopens previously finished workers;
  * only supplements NEW Worker model calls with format-only instructions;
  * accepts repeated JSON objects only when the complete decoded objects are identical;
  * rejects distinct JSON objects and retains their raw response unchanged;
  * leaves Controller parsing, prior saved-call replay, FRESH science isolation, and
    journal history unchanged; records any normalization in stdout, not as evidence.

The underlying, pre-existing G14 runner and exact-id guard remain authoritative.
Continuation is allowed beyond the pinned 1572-event prefix, but every paid run
requires an explicit --expect-events value matching the freshly verified state.
The script does not claim a scientific result or source read.
"""
from __future__ import annotations
import argparse, contextlib, hashlib, json, os, sys, threading
from pathlib import Path
from types import SimpleNamespace

BASELINE_EVENTS = 1572
BASELINE_HEAD = 'ac14a7a7b25fd4018768d8b0309a0ec0890c47541647448c7885680a3b9becb1'
WORK_ID = 'W_P0_bounded_joint_feasibility_015'
FAILED_CALLS = (
    'WK_W_P0_mechanism_specific_primary_retrieval_013_00005',
    'WK_W_P0_bounded_joint_feasibility_014_00001',
)
FORMAT_NOTICE = ("\nOUTPUT SERIALIZATION CONTRACT (format only, not research guidance): "
    "Return EXACTLY ONE complete top-level JSON OBJECT. Do not repeat the object, "
    "append a second answer, include multiple candidate JSON outputs, Markdown, "
    "or explanatory text outside the JSON object. Continue scientific reasoning "
    "freely inside scientific_text; research/RETURN/HOLD and tool choices are yours.\n")


def _no_duplicate_keys(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError('DUPLICATE_KEY_IN_JSON_OBJECT:' + k)
        out[k] = v
    return out


def parse_json_stream(s):
    """Only a whitespace-delimited stream of complete JSON dictionaries, no repairs."""
    if not isinstance(s, str) or len(s) > 1_000_000:
        return None
    decoder = json.JSONDecoder()
    pos = 0
    out = []
    while pos < len(s):
        while pos < len(s) and s[pos].isspace():
            pos += 1
        if pos == len(s):
            break
        try:
            obj, end = decoder.raw_decode(s, pos)
            # Reject duplicate object keys and non-JSON constants in each document.
            obj = json.loads(s[pos:end], object_pairs_hook=_no_duplicate_keys,
                             parse_constant=lambda x: (_ for _ in ()).throw(ValueError('INVALID_CONSTANT:' + x)))
        except (ValueError, TypeError, json.JSONDecodeError):
            return None
        if not isinstance(obj, dict) or end <= pos:
            return None
        out.append(obj)
        pos = end
        if len(out) > 4:
            return None
    return out if out else None


def _canon(o):
    return json.dumps(o, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')


def classify_duplicate(s):
    """Returns (classification, safe_object_or_None, count, note)."""
    items = parse_json_stream(s)
    if items is None:
        return 'NOT_CLEAN_JSON_STREAM', None, 0, None
    if len(items) == 1:
        return 'SINGLE_JSON', items[0], 1, None
    hashes = [hashlib.sha256(_canon(x)).hexdigest() for x in items]
    if len(set(hashes)) == 1:
        return 'IDENTICAL_COMPLETE_DUPLICATE', items[0], len(items), hashes[0]
    # No selection of first/last, no field merging or guessed author intent.
    return 'DISTINCT_MULTIPLE_JSON_BLOCK_FAIL_CLOSED', None, len(items), hashes


def top_level_differences(objs):
    if not objs or len(objs)<2:
        return []
    first=objs[0]
    names=set(first)
    for obj in objs[1:]:names.update(obj)
    return sorted(k for k in names if any(k not in obj or obj[k]!=first.get(k) for obj in objs))


def verify_current_state(experiment):
    import G14_LEVEL2_TRACE_CONTINUATION_20261030 as trace
    exp, cycle, mods, j, s, events = trace.verify(experiment, expect_stage=True)
    assert len(events) >= BASELINE_EVENTS, 'JOURNAL_BEFORE_1572_BASELINE'
    assert mods.sha(mods.canon(events[BASELINE_EVENTS-1])) == BASELINE_HEAD, '1572_PREFIX_CHANGED'
    assert Path(cycle['population_root']).resolve() == (exp/'CYCLE_014'/'POPULATION').resolve(), 'NOT_G14_ROOT'
    assert all(v['state'] == 'SAVED' for v in s.model_calls.values()), 'UNSAVED_PROVIDER_CALL'
    assert WORK_ID in s.work, 'TARGET_WORK_NOT_FOUND'
    return exp, cycle, mods, j, s, events


def saved_failure_audit(j, s):
    from e2core.provider import content_from_wire, strict_envelope
    ans=[]
    for ident in FAILED_CALLS:
        assert ident in s.model_calls, 'PREVIOUS_CALL_MISSING:' + ident
        c=s.model_calls[ident]
        assert c['state']=='SAVED', 'PREVIOUS_MODEL_CALL_NOT_SAVED'
        raw=j.raw(c['response_blob'])
        try:
            rendered=content_from_wire(raw)
            result, obj, count, hashes=classify_duplicate(rendered)
            objs=parse_json_stream(rendered)
            # Do not change science even if identical; historical Work is DONE.
            ans.append({'call_id':ident,'classification':result,'envelopes':count,
                'decoded_sha256':hashes,
                'different_top_level_fields':top_level_differences(objs),
                'same_tool_request':(all(x.get('tool_request')==objs[0].get('tool_request') for x in objs)
                                     if objs is not None and len(objs)>1 else None),
                'historical_response_reused':False,
                'strict_current_parser_accepts':strict_envelope(rendered) is not None})
        except Exception as e:
            ans.append({'call_id':ident,'classification':'NOT_READABLE','exception_type':type(e).__name__})
    return ans


@contextlib.contextmanager
def activate(root, stats):
    """Composition-safe monkeypatch scoped to one root; nothing permanent on disk."""
    from e2core.provider import DurableModel
    from e2core import engine as e2engine
    root=Path(root).expanduser().resolve(strict=True)
    old_call=DurableModel.call
    old_step=e2engine.Engine.worker_step
    old_parse=e2engine.strict_envelope
    local=threading.local()

    def worker_call(self, ident, actor, work_id, system, payload):
        if Path(self.j.root).resolve() != root or actor != 'WORKER':
            return old_call(self, ident, actor, work_id, system, payload)
        state=self.j.verify()
        if ident in state.model_calls:
            # Exact byte-for-byte durable replay: do not change system or payload.
            return old_call(self, ident, actor, work_id, system, payload)
        if not (isinstance(system,str) and isinstance(payload,dict)):
            return old_call(self, ident, actor, work_id, system, payload)
        stats['new_worker_format_prompts']+=1
        return old_call(self, ident, actor, work_id, system+FORMAT_NOTICE, payload)

    def worker_step(self, wid):
        if Path(self.j.root).resolve()!=root:
            return old_step(self, wid)
        prev=getattr(local, 'in_worker', False)
        local.in_worker=True
        try:
            return old_step(self, wid)
        finally:
            local.in_worker=prev

    def worker_parse(text):
        ordinary=old_parse(text)
        if ordinary is not None or not getattr(local,'in_worker',False):
            return ordinary
        kind, obj, count, digest=classify_duplicate(text)
        if kind=='IDENTICAL_COMPLETE_DUPLICATE':
            stats['identical_duplicate_envelopes_collapsed']+=1
            print(json.dumps({'status':'G14_IDENTICAL_DUPLICATE_ENVELOPE_COLLAPSED',
               'count':count,'canonical_sha256':digest,
               'raw_provider_response_and_full_model_text_preserved':True,
               'science_certification':False}),flush=True)
            return obj
        if kind=='DISTINCT_MULTIPLE_JSON_BLOCK_FAIL_CLOSED':
            stats['distinct_duplicate_envelopes_rejected']+=1
            print(json.dumps({'status':'G14_DISTINCT_MULTIPLE_ENVELOPES_REJECTED',
               'count':count, 'object_sha256':digest,
               'none_selected':True,'raw_response_preserved':True,
               'not_scientific_failure':True}),flush=True)
        return None

    DurableModel.call=worker_call
    e2engine.Engine.worker_step=worker_step
    e2engine.strict_envelope=worker_parse
    try:
        yield
    finally:
        e2engine.strict_envelope=old_parse
        e2engine.Engine.worker_step=old_step
        DurableModel.call=old_call


def selftest():
    import tempfile, types
    a={'scientific_text':'x', 'next_action':'RETURN', 'assets':[], 'new_problems':[], 'tool_request':None}
    b={**a, 'scientific_text':'different science'}
    sa=json.dumps(a)
    sb=json.dumps(b)
    assert classify_duplicate(sa)[0]=='SINGLE_JSON'
    assert classify_duplicate(sa+'\n\n'+sa)[0]=='IDENTICAL_COMPLETE_DUPLICATE'
    assert classify_duplicate(sa+'\n'+sb)[0]=='DISTINCT_MULTIPLE_JSON_BLOCK_FAIL_CLOSED'
    assert classify_duplicate('```json\n'+sa+'\n```')[0]=='NOT_CLEAN_JSON_STREAM'
    assert classify_duplicate(sa+'oops')[0]=='NOT_CLEAN_JSON_STREAM'
    assert classify_duplicate('['+sa+']')[0]=='NOT_CLEAN_JSON_STREAM'
    assert classify_duplicate(sa+'\n\n'+json.dumps(dict(reversed(list(a.items())))))[0]=='IDENTICAL_COMPLETE_DUPLICATE'
    assert classify_duplicate(sa+'\n'+sa+'\n'+sa)[0]=='IDENTICAL_COMPLETE_DUPLICATE'
    assert classify_duplicate(sa+'\n'+sa+'\n'+sa+'\n'+sa+'\n'+sa)[0]=='NOT_CLEAN_JSON_STREAM'
    assert classify_duplicate('{"a":1,"a":2}\n{"a":1,"a":2}')[0]=='NOT_CLEAN_JSON_STREAM'
    assert classify_duplicate(sa+'\n{}')[1] is None
    assert 'EXACTLY ONE' in FORMAT_NOTICE
    assert BASELINE_EVENTS==1572
    assert top_level_differences([a,b])==['scientific_text']
    # End-to-end mock of guarded Worker call, parser, Controller non-interference,
    # saved-call replay, journal preservation and original model response storage.
    pkg=types.ModuleType('e2core');pkg.__path__=[]
    provider=types.ModuleType('e2core.provider')
    eng=types.ModuleType('e2core.engine')
    prior={name:sys.modules.get(name) for name in ('e2core','e2core.provider','e2core.engine')}
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp).resolve()
        class FakeJournal:
            def __init__(self):self.root=root;self.calls={}
            def verify(self):return SimpleNamespace(model_calls=self.calls)
        class FakeDurableModel:
            def __init__(self,j):self.j=j;self.systems=[];self.response=sa+'\n'+sa
            def call(self,ident,actor,work_id,system,payload):
                self.systems.append((ident,actor,system,payload))
                self.j.calls[ident]={'state':'SAVED'}
                return self.response
        class FakeEngine:
            def __init__(self,j,model):self.j=j;self.model=model
            def worker_step(self,wid):
                text=self.model.call('WK_'+wid,'WORKER',wid,'ORIGINAL_SYSTEM',{})
                return eng.strict_envelope(text)
        provider.DurableModel=FakeDurableModel
        eng.Engine=FakeEngine
        eng.strict_envelope=lambda t:json.loads(t) if t==sa else None
        sys.modules['e2core']=pkg
        sys.modules['e2core.provider']=provider
        sys.modules['e2core.engine']=eng
        pkg.engine=eng;pkg.provider=provider
        try:
            j=FakeJournal();model=FakeDurableModel(j);e=FakeEngine(j,model)
            stats={'new_worker_format_prompts':0,
                'identical_duplicate_envelopes_collapsed':0,
                'distinct_duplicate_envelopes_rejected':0}
            with activate(root,stats):
                got=e.worker_step('W_TEST_00001')
                assert got==a
                assert model.systems[-1][2].endswith(FORMAT_NOTICE)
                assert stats['identical_duplicate_envelopes_collapsed']==1
                # Existing saved calls must keep exactly the original request.
                e.worker_step('W_TEST_00001')
                assert model.systems[-1][2]=='ORIGINAL_SYSTEM'
                # Distinct simultaneous answers are rejected, not selected.
                model.response=sa+'\n'+sb
                assert e.worker_step('W_TEST_00002') is None
                assert stats['distinct_duplicate_envelopes_rejected']==1
                # Controller's parsing path is unchanged by Worker-only recovery.
                assert eng.strict_envelope(sa+'\n'+sa) is None
                model.call('CTRL_D00001','CONTROLLER',None,'ORIGINAL_SYSTEM',{})
                assert model.systems[-1][2]=='ORIGINAL_SYSTEM'
                assert len(j.calls)==3
            assert eng.Engine.worker_step is FakeEngine.worker_step
        finally:
            for name,value in prior.items():
                if value is None:sys.modules.pop(name,None)
                else:sys.modules[name]=value
    print(json.dumps({'status':'G14_SINGLE_ENVELOPE_SELFTEST_OK','checks':22,
        'paid_calls':0,'journal_modified':False}),flush=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('command',choices=['selftest','preflight','run'])
    ap.add_argument('--experiment')
    ap.add_argument('--trace-dir')
    ap.add_argument('--expect-events',type=int,help='Exact current journal event count; required for paid run')
    args,forward=ap.parse_known_args()
    if args.command=='selftest':
        assert not forward,'UNEXPECTED_SELFTEST_ARGS'
        return selftest()
    assert args.experiment,'EXPERIMENT_REQUIRED'
    exp,cycle,mods,j,s,events=verify_current_state(args.experiment)
    assert args.expect_events is None or len(events)==args.expect_events, 'CURRENT_EVENT_COUNT_CHANGED'
    audits=saved_failure_audit(j,s)
    report={'status':'G14_SINGLE_ENVELOPE_PREFLIGHT_OK_NO_PAID',
      'events':len(events),'expected_events':args.expect_events,'current_head':mods.sha(mods.canon(events[-1])),
      'verified_1572_prefix':BASELINE_HEAD, 'generation':14,
      'active_works':sorted(k for k,v in s.work.items() if v['status']=='ACTIVE'),
      'prior_duplicate_response_audit':audits,
      'all_model_calls_saved':True,'journal_modified':False,
      'paid_calls':0,'fresh_scientific_context_unchanged':True}
    if args.command=='preflight':
        assert not forward,'UNEXPECTED_PREFLIGHT_ARGS'
        assert (exp/'STOP_REQUESTED').is_file(),'STOP_MARKER_REQUIRED_FOR_PREFLIGHT'
        print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
        return
    assert args.command=='run'
    assert args.expect_events is not None and args.expect_events >= BASELINE_EVENTS, 'EXPLICIT_CURRENT_EVENT_COUNT_REQUIRED'
    assert len(events)==args.expect_events, 'START_STATE_CHANGED_INSPECT_AGAIN'
    assert s.work[WORK_ID]['status']=='ACTIVE','EXPECTED_WORK_NOT_ACTIVE'
    assert args.trace_dir,'TRACE_DIR_REQUIRED'
    assert '--paid' in forward and os.getenv('FAKG_RESEARCH_ALLOW_PAID')=='YES','EXPLICIT_PAID_APPROVAL_REQUIRED'
    assert not (exp/'STOP_REQUESTED').exists(),'STOP_REQUESTED_PRESENT'
    assert '--max-operational-segments' in forward,'BOUND_REQUIRED'
    ix=forward.index('--max-operational-segments')
    assert ix+1<len(forward) and forward[ix+1]=='1','ONE_SEGMENT_ONLY'
    import G14_LEVEL2_TRACE_CONTINUATION_20261030 as trace
    import G14_EXACT_ID_REQUEST_GUARD_20261030 as guard
    old_activate=guard.activate
    stats={'new_worker_format_prompts':0,'identical_duplicate_envelopes_collapsed':0,
           'distinct_duplicate_envelopes_rejected':0}
    @contextlib.contextmanager
    def composed_activate(root):
        with old_activate(root):
            with activate(root,stats):
                yield
    try:
        guard.activate=composed_activate
        sys.argv=[str(Path(trace.__file__).resolve()),'run','--experiment',str(exp),
                  '--trace-dir',str(args.trace_dir),*forward]
        print(json.dumps(report|{'status':'G14_SINGLE_ENVELOPE_RUN_BEGIN'},ensure_ascii=False),flush=True)
        result=trace.main()
        print(json.dumps({'status':'G14_SINGLE_ENVELOPE_RUN_SUMMARY',**stats,
          'controller_not_forced':True,'old_failed_works_not_reopened':True,
          'raw_model_responses_remain_preserved':True},ensure_ascii=False),flush=True)
        return result
    finally:
        guard.activate=old_activate


if __name__=='__main__':
    try:
        sys.exit(main() or 0)
    except Exception as e:
        print(json.dumps({'status':'G14_SINGLE_ENVELOPE_OPERATIONAL_PAUSE',
            'error_type':type(e).__name__,'detail':str(e),
            'not_scientific_hold':True},ensure_ascii=False),file=sys.stderr)
        sys.exit(3)
