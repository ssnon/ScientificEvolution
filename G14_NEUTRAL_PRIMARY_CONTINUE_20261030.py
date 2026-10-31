#!/usr/bin/env python3
"""G14-only public-primary *locator* feedback for new FRESH literature Worker calls.

Requires the user's original G14_LEVEL2_TRACE_CONTINUATION_20261030.py and
G14_EXACT_ID_REQUEST_GUARD_20261030.py in the same WSL Python path. Does NOT
create model-generated claims, fabricate fulltext receipts, change original
Journal events, or bypass the native tool backend or strict validators.

Proof of prior external access is a separate operator audit, NOT Work evidence.
The model must independently request literature_research/read_fulltext for
actual Journal source registration. Scientific decisions remain autonomous.
"""
from __future__ import annotations
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import sys

WORK_ID = 'W_P0_primary_sers_precedent_retrieval_002'
EXPECTED_PROBE_SHA256 = '6bbf1483f67f0707d841c425f68cc87496541f9f0bbe6b0dd534ee89c91c99cb'
PREFIX_1217 = '8c407b16508578e47dd6b49ae40337d193d35f7debc39e2e450bf5527b95f885'
FULLTEXT_CLASSES = frozenset({'OA_FULLTEXT_TEXT', 'OA_PDF_TEXT', 'OA_SUPPLEMENT_TEXT'})
PAPERS = {
    'PMC13325844': '10.1021/acsnano.6c03605',
    'PMC12285619': '10.1002/smtd.202402107',
}


def digest_bytes(b):
    return hashlib.sha256(b).hexdigest()


def validate_probe(probe_path):
    p = Path(probe_path).expanduser().resolve(strict=True)
    raw = p.read_bytes()
    assert digest_bytes(raw) == EXPECTED_PROBE_SHA256, 'EXTERNAL_PROBE_HASH_CHANGED'
    report = json.loads(raw)
    assert report['status'] == 'G14_NATIVE_PRIMARY_LITERATURE_FREE_ACCESS_PROBE'
    assert report['probe_not_imported_into_journal'] is True
    assert report['model_calls_sent'] == 0
    assert len(report['papers']) == 2
    results = []
    for row in report['papers']:
        paper = row['paper']
        pmcid = paper['pmcid']
        assert pmcid in PAPERS and paper['doi'] == PAPERS[pmcid], 'UNEXPECTED_PAPER'
        assert row['fulltext_access_confirmed'] is True
        counts = sum(len(s['response'].get('paragraphs', [])) for s in row['steps']
                     if s['arguments'].get('action') == 'read_fulltext'
                     and s['response'].get('status') == 'DELIVERED'
                     and s['response'].get('evidence_class') == 'OA_FULLTEXT_TEXT')
        assert counts == row['fulltext_paragraphs_retrieved'] and counts > 0, 'FULLTEXT_NOT_VERIFIED'
        # Locator only: no passages, AI-written interpretation, or inherited
        # scientific hypothesis is passed to this independent FRESH Work.
        results.append({'pmcid':pmcid, 'doi':paper['doi'], 'title':paper['title'],
                        'operator_access_test_paragraph_count':counts})
    assert {r['pmcid'] for r in results} == set(PAPERS)
    return results


def verify_current_state(experiment):
    import G14_LEVEL2_TRACE_CONTINUATION_20261030 as trace
    exp, cycle, mods, j, s, events = trace.verify(experiment, expect_stage=True)
    assert len(events) >= 1217, 'BEFORE_1217_JOURNAL_CHECKPOINT'
    assert mods.sha(mods.canon(events[1216])) == PREFIX_1217, 'JOURNAL_PREFIX_CHANGED'
    assert (exp / 'CYCLE_014' / 'POPULATION').resolve() == Path(cycle['population_root']).resolve()
    w = s.work[WORK_ID]
    assert w['mode'] == 'FRESH', 'FRESH_ISOLATION_NOT_PRESENT'
    assert w['status'] == 'ACTIVE', 'LITERATURE_WORK_NO_LONGER_ACTIVE'
    assert all(rec['state'] == 'SAVED' for rec in s.model_calls.values())
    return exp, cycle, mods, j, s, events


def native_fulltext_already_read(j, state):
    for row in state.tool_results.values():
        if row['work_id'] != WORK_ID:
            continue
        obj = json.loads(j.raw(row['result_blob']))
        if (obj.get('status') == 'DELIVERED'
                and obj.get('evidence_class') in FULLTEXT_CLASSES):
            return True
    return False


def supplemental_feedback(locators):
    return {
        'type': 'OPERATOR_VERIFIED_PUBLIC_PRIMARY_LOCATOR_AVAILABILITY_ONLY',
        'provenance_kind': 'INDEPENDENT_OPERATOR_HTTP_ACCESS_PROBE_OUTSIDE_JOURNAL',
        'external_probe_sha256': EXPECTED_PROBE_SHA256,
        'independent_public_primary_locators': locators,
        'strict_boundary': ('These article identities and external access checks are public-source '
            'locator facts, not findings, prior AI hypotheses, or evidence this Work has obtained. '
            'Any literature-based scientific claim requires this Work to issue its own '
            'literature_research action=read_fulltext with pmcid and inspect its saved tool result. '
            'If successfully DELIVERED, use the linked_source_id returned by this Work, not an '
            'operator source id. Distinguish measured methods/results from authors\' mechanisms. '
            'External SI archive access was NOT established. None of these claims are certified.'),
        'scientific_discretion': ('Select papers, theoretical tasks, tests, RETURN or HOLD freely. '
            'The presence of these neutral locators is not an instruction to adopt a conclusion '
            'or produce a new hypothesis. Do not infer that a paper supports a mechanism until read.'),
        'isolation': 'No historical AI asset or other Work content supplied to FRESH Worker.',
    }


def with_public_locators(system, payload, locators):
    assert isinstance(system,str) and isinstance(payload,dict), 'UNEXPECTED_PROVIDER_INPUT'
    result = dict(payload)
    assert 'operator_public_primary_locator_feedback' not in result, 'ALREADY_INJECTED'
    result['operator_public_primary_locator_feedback'] = supplemental_feedback(locators)
    # Request-time, after existing memory compaction; original input untouched.
    appendix = ('\nPUBLIC PRIMARY SOURCE LOCATOR AVAILABILITY: The operator_public_primary_locator_feedback '
        'field contains only publicly accessible article identifiers independently tested by an '
        'operator, NOT source evidence yet acquired by this Work and NOT previous AI research. '
        'Native literature_research read_fulltext can use these PMCIDs. The scientific research '
        'choice and any interpretation remain yours. Never assert a fulltext read without a '
        'DELIVERED source record in your own Journal.\n')
    return system + appendix, result


@contextlib.contextmanager
def activate(expected_root,locators):
    """Temporary, scope-limited provider boundary wrapper; replay-safe."""
    from e2core.provider import DurableModel
    root = Path(expected_root).expanduser().resolve(strict=True)
    old = DurableModel.call
    def wrapper(self,ident,actor,work_id,system,payload):
        if Path(self.j.root).resolve() != root or actor != 'WORKER' or work_id != WORK_ID:
            return old(self,ident,actor,work_id,system,payload)
        s = self.j.verify()
        # Existing call replay MUST receive the identical unaltered request.
        if ident in s.model_calls:
            return old(self,ident,actor,work_id,system,payload)
        assert s.work[WORK_ID]['mode'] == 'FRESH', 'FRESH_WORK_NOT_FRESH'
        if native_fulltext_already_read(self.j,s):
            return old(self,ident,actor,work_id,system,payload)
        system,payload = with_public_locators(system,payload,locators)
        return old(self,ident,actor,work_id,system,payload)
    DurableModel.call = wrapper
    try:
        yield
    finally:
        DurableModel.call = old


def selftest():
    from types import SimpleNamespace
    data = [
        {'pmcid':'PMC13325844','doi':PAPERS['PMC13325844'],'title':'Neutral paper A',
         'operator_access_test_paragraph_count':35},
        {'pmcid':'PMC12285619','doi':PAPERS['PMC12285619'],'title':'Neutral paper B',
         'operator_access_test_paragraph_count':45},
    ]
    original = {'own_recorded_tool_attempts':3}
    system,payload=with_public_locators('ORIGINAL_SYSTEM',original,data)
    assert original=={'own_recorded_tool_attempts':3}
    assert system.startswith('ORIGINAL_SYSTEM') and system != 'ORIGINAL_SYSTEM'
    assert payload['operator_public_primary_locator_feedback']['independent_public_primary_locators']==data
    assert not any('charge_trap' in str(r).lower() for r in data)
    p = SimpleNamespace(work_id=WORK_ID)
    assert p.work_id == WORK_ID
    # A mock provider boundary verifies replay safety and scope isolation.
    import tempfile
    import types
    call_log=[]
    pkg=types.ModuleType('e2core');pkg.__path__=[]
    provider_mod=types.ModuleType('e2core.provider')
    class MockDurableModel:
        def call(self,ident,actor,work_id,system,payload):
            call_log.append((ident,actor,work_id,system,payload))
            return {'status':'MOCK_ONLY'}
    provider_mod.DurableModel=MockDurableModel
    old_pkg=sys.modules.get('e2core')
    old_provider=sys.modules.get('e2core.provider')
    sys.modules['e2core']=pkg
    sys.modules['e2core.provider']=provider_mod
    try:
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve()
            class MockJournal:
                def __init__(self):
                    self.root=root
                    self.calls={}
                    self.results=[]
                def verify(self):
                    return SimpleNamespace(model_calls=self.calls,
                        work={WORK_ID:{'mode':'FRESH'}}, tool_results={})
            mdl=MockDurableModel()
            mdl.j=MockJournal()
            with activate(root,data):
                mdl.call('WK_NEW','WORKER',WORK_ID,'SYSTEM',original)
                assert 'operator_public_primary_locator_feedback' in call_log[-1][4]
                assert original == {'own_recorded_tool_attempts':3}
                mdl.j.calls['WK_REPLAY']={'state':'SAVED'}
                mdl.call('WK_REPLAY','WORKER',WORK_ID,'SYSTEM',original)
                assert call_log[-1][3]=='SYSTEM' and call_log[-1][4] is original
                mdl.call('WK_OTHER','WORKER','W_OTHER','SYSTEM',original)
                assert call_log[-1][4] is original
                mdl.call('CTRL_D999','CONTROLLER',None,'SYSTEM',original)
                assert call_log[-1][4] is original
    finally:
        if old_pkg is None:sys.modules.pop('e2core',None)
        else:sys.modules['e2core']=old_pkg
        if old_provider is None:sys.modules.pop('e2core.provider',None)
        else:sys.modules['e2core.provider']=old_provider
    print(json.dumps({'status':'G14_NEUTRAL_LOCATOR_SELFTEST_OK','checks':9,
                      'model_calls_sent':0,'journal_modified':False}))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['selftest','preflight','run'])
    p.add_argument('--experiment')
    p.add_argument('--trace-dir')
    p.add_argument('--probe',default=str(Path.home()/'G14_PRIMARY_FULLTEXT_PROBE.json'))
    opts,forward=p.parse_known_args()
    if opts.command=='selftest':
        assert not forward, 'UNKNOWN_SELFTEST_OPTIONS'
        selftest();return 0
    assert opts.experiment, 'EXPERIMENT_REQUIRED'
    assert opts.command!='preflight' or not forward, 'UNKNOWN_PREFLIGHT_OPTIONS'
    locators=validate_probe(opts.probe)
    exp,cycle,mods,j,s,events=verify_current_state(opts.experiment)
    evidence_seen=native_fulltext_already_read(j,s)
    summary={'status':'G14_NEUTRAL_PRIMARY_PREFLIGHT_OK_NO_PAID',
      'current_events':len(events), 'current_head':mods.sha(mods.canon(events[-1])),
      'work_id':WORK_ID, 'work_status':s.work[WORK_ID]['status'],
      'own_fulltext_already_acquired':evidence_seen,
      'public_fulltext_locators_available':len(locators),
      'probe_sha256':EXPECTED_PROBE_SHA256,
      'journal_modified':False, 'model_calls_sent':0,
      'FRESH_source_boundary_preserved':True}
    if opts.command=='preflight':
        assert (exp/'STOP_REQUESTED').is_file(),'STOP_REQUESTED_REQUIRED_FOR_PREFLIGHT'
        print(json.dumps(summary,ensure_ascii=False,indent=2));return 0
    assert opts.command=='run'
    if not opts.trace_dir:raise RuntimeError('TRACE_DIR_REQUIRED')
    if '--paid' not in forward or os.getenv('FAKG_RESEARCH_ALLOW_PAID')!='YES':
        raise RuntimeError('PAID_RUN_REQUIRES_EXPLICIT_--paid_AND_ENV_APPROVAL')
    if (exp/'STOP_REQUESTED').exists():
        raise RuntimeError('STOP_REQUESTED_PRESENT')
    if '--max-operational-segments' not in forward:
        raise RuntimeError('EXPLICIT_SEGMENT_LIMIT_REQUIRED')
    i=forward.index('--max-operational-segments')
    if i+1>=len(forward) or forward[i+1]!='1':
        raise RuntimeError('ONLY_ONE_OPERATIONAL_SEGMENT_PER_INVOCATION')
    print(json.dumps(summary|{'status':'G14_NEUTRAL_PUBLIC_LOCS_RUN_BEGIN'},ensure_ascii=False),flush=True)
    import G14_LEVEL2_TRACE_CONTINUATION_20261030 as trace
    import G14_EXACT_ID_REQUEST_GUARD_20261030 as guard
    original_activate = guard.activate
    @contextlib.contextmanager
    def composed_activate(root):
        with original_activate(root):
            with activate(root,locators):
                yield
    try:
        guard.activate=composed_activate
        sys.argv=[str(Path(trace.__file__).resolve()),'run',
                  '--experiment',str(exp),'--trace-dir',opts.trace_dir,*forward]
        return trace.main()
    finally:
        guard.activate=original_activate

if __name__=='__main__':
    try:sys.exit(main())
    except Exception as exc:
        print(json.dumps({'status':'G14_NEUTRAL_PRIMARY_OPERATIONAL_PAUSE',
          'exception_type':type(exc).__name__, 'detail':str(exc),
          'not_scientific_hold':True},ensure_ascii=False),file=sys.stderr)
        sys.exit(3)
