#!/usr/bin/env python3
"""Forensic read-only inspection of SAVED model responses for G14 (no paid calls).

Run inside ScientificEvolution with PYTHONPATH pointing to runtime. The script
verifies the immutable 1,572-event journal prefix, then inspects exact archived
provider response bytes for selected WORKER calls. It never repairs, replays,
appends, retries, or creates scientific assets, and sends no network requests.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

BASELINE_EVENTS = 1572
BASELINE_HEAD = "ac14a7a7b25fd4018768d8b0309a0ec0890c47541647448c7885680a3b9becb1"
CALLS = [
    "WK_W_P0_mechanism_specific_primary_retrieval_013_00005",
    "WK_W_P0_bounded_joint_feasibility_014_00001",
    "WK_W_P0_bounded_joint_feasibility_015_00001",  # valid control
]

def parse_response(raw: bytes, strict_envelope):
    out = {"provider_raw_bytes": len(raw), "provider_raw_sha256": hashlib.sha256(raw).hexdigest()}
    try:
        env = json.loads(raw)
        if not isinstance(env, dict):
            out["provider_parse_error"] = "OUTER_NOT_OBJECT"
            return out
        out["outer_fields"] = sorted(env.keys())
        out["usage"] = env.get("usage")
        if env.get("error"):
            out["provider_error"] = str(env["error"])[:400]
        choices = env.get("choices") or []
        if not choices:
            out["provider_parse_error"] = "NO_CHOICES"
            return out
        choice = choices[0]
        out["finish_reason"] = choice.get("finish_reason")
        message = choice.get("message") or {}
        content = message.get("content")
        if isinstance(content,dict):
            content = json.dumps(content,ensure_ascii=False)
        out["content_type"] = type(content).__name__
        if not isinstance(content, str):
            out["provider_parse_error"] = "NON_STRING_MESSAGE_CONTENT"
            return out
        out["content_chars"] = len(content)
        out["content_start"] = content[:260]
        out["content_end"] = content[-260:]
        out["content_ends_with_closing_brace"] = content.rstrip().endswith('}')
        out["content_brace_counts"] = {"open":content.count('{'),"close":content.count('}')}
        try:
            decoded=json.loads(content)
            out["json_loads_ok"] = True
            out["decoded_type"] = type(decoded).__name__
            if isinstance(decoded,dict):out["decoded_keys"] = sorted(decoded.keys())
        except json.JSONDecodeError as ex:
            out["json_loads_ok"] = False
            out["json_error"] = {"message":ex.msg,"line":ex.lineno,"column":ex.colno,"pos":ex.pos,
                                 "context":content[max(0,ex.pos-100):min(len(content),ex.pos+100)]}
        parsed=strict_envelope(content)
        out["strict_envelope_ok"] = parsed is not None
        if isinstance(parsed,dict):
            out["strict_envelope_keys"] = sorted(parsed.keys())
            out["next_action"] = parsed.get("next_action")
            out["scientific_text_is_str"] = isinstance(parsed.get("scientific_text"),str)
        return out
    except Exception as ex:
        out["provider_parse_error"] = type(ex).__name__ + ":" + str(ex)[:300]
        return out

def selftest():
    # Lightweight imitation of the exact single-envelope parser boundary.
    def strict_envelope(text):
        try:
            o=json.loads(text)
            return o if isinstance(o,dict) else None
        except (TypeError,ValueError):return None
    def provider(content,finish_reason='stop'):
        return json.dumps({"choices":[{"finish_reason":finish_reason,"message":{"content":content}}],"usage":{"completion_tokens":7}}).encode()
    good=parse_response(provider('{"scientific_text":"ok","next_action":"RETURN"}'),strict_envelope)
    assert good['strict_envelope_ok'] and good['finish_reason']=='stop'
    broken=parse_response(provider('{"scientific_text":"unfinished','length'),strict_envelope)
    assert not broken['strict_envelope_ok'] and broken['finish_reason']=='length'
    nonstring=parse_response(json.dumps({'choices':[{'message':{'content':['not','text']}}]}).encode(),strict_envelope)
    assert nonstring['provider_parse_error']=='NON_STRING_MESSAGE_CONTENT'
    invalid=parse_response(b'not json',strict_envelope)
    assert invalid['provider_parse_error'].startswith('JSONDecodeError')
    print(json.dumps({'status':'G14_FORMAT_READONLY_SELFTEST_OK','checks':4,'paid_calls':0,'journal_modified':False}))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['selftest','inspect'])
    p.add_argument('--experiment',default=os.path.expanduser('~/ScientificEvolution_runs/AUTONOMOUS_POPULATION_20261029'))
    p.add_argument('--root',help='Override exact G14 POPULATION Journal root')
    p.add_argument('--output',help='Write the diagnostic JSON to a separate file (outside Journal root)')
    args=p.parse_args()
    if args.command=='selftest':selftest();return 0
    from e2core.core import EvolutionJournal,canon,sha
    from e2core.provider import strict_envelope
    root=Path(args.root or (Path(args.experiment)/'CYCLE_014'/'POPULATION')).resolve()
    if not (root/'manifest.json').is_file():raise SystemExit('JOURNAL_ROOT_NOT_FOUND: '+str(root))
    j=EvolutionJournal(root)
    state=j.verify()
    events=j._events()
    if len(events)<BASELINE_EVENTS:raise SystemExit('JOURNAL_EVENT_COUNT_BELOW_1572')
    actual=sha(canon(events[BASELINE_EVENTS-1]))
    if actual!=BASELINE_HEAD:raise SystemExit('JOURNAL_PREFIX_DIVERGED: '+actual)
    results=[]
    for callid in CALLS:
        call=state.model_calls.get(callid)
        if not call:
            results.append({'call_id':callid,'error':'CALL_NOT_PRESENT'});continue
        entry={'call_id':callid,'state':call.get('state'),'work_id':call.get('work_id'),
               'request_blob_sha256':call.get('request_blob'),'response_blob_sha256':call.get('response_blob')}
        if call.get('state')!='SAVED':
            entry['error']='CALL_NOT_SAVED'
        else:
            raw=j.raw(call['response_blob'])
            entry.update(parse_response(raw,strict_envelope))
            request=json.loads(j.raw(call['request_blob']))
            entry['request_max_tokens']=request.get('max_tokens')
            entry['request_model']=request.get('model')
            entry['request_messages_chars']=[len(str(m.get('content',''))) for m in request.get('messages',[])]
        results.append(entry)
    report={'status':'G14_FORMAT_FAILURE_READONLY_DIAGNOSTIC','journal_events':len(events),
            'verified_prefix_events':BASELINE_EVENTS,'verified_prefix_head':actual,
            'journal_modified':False,'paid_calls':0,'network_calls':0,'results':results}
    if args.output:
        dest=Path(args.output).expanduser().resolve()
        if dest==root or root in dest.parents:raise SystemExit('OUTPUT_INSIDE_JOURNAL_ROOT_FORBIDDEN')
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        print(json.dumps({'status':'G14_FORMAT_DIAG_WRITTEN','path':str(dest),'records':len(results),'paid_calls':0,'journal_modified':False}))
    else:
        print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0

if __name__=='__main__':sys.exit(main())
