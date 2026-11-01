"""M19: provenance-aware, on-demand inherited evidence access.

Not a research policy; does not select scientific winners, re-execute tools, or
certify source interpretation. FRESH isolation is a hard security boundary.
"""
from __future__ import annotations
import json
from collections import Counter

ARCHIVED_KINDS = {
    'INHERITED_REAL_EXECUTION_TOOL_RESULT_NOT_NEW_OBSERVATION',
    'INHERITED_SCIENCE_TOOL_EXECUTION_NOT_NEW_OBSERVATION',
}


def archived_record(j, state, sid):
    rec = state.sources.get(sid)
    if not (isinstance(sid, str) and sid.startswith('SRC_INHERITED_TOOL_')
            and rec and rec.get('kind') == 'EXTERNAL_AUDIT'):
        return None
    item = json.loads(j.raw(rec['blob']))
    if (not isinstance(item, dict) or item.get('kind') not in ARCHIVED_KINDS
            or not isinstance(item.get('original_returned_data'), dict)
            or not isinstance(item.get('evidence_class'), str)
            or not isinstance(item.get('original_tool_id'), str)):
        return None
    return item


def archive_summary(sid, item):
    data = item['original_returned_data']
    result = data.get('result', {})
    if not isinstance(result, dict):
        result = {}
    request = data.get('request', {})
    if not isinstance(request, dict):
        request = {}
    args = request.get('arguments', {})
    if not isinstance(args, dict):
        args = {}
    return {
        'source_id': sid,
        'tool_kind': request.get('kind') or item.get('tool_kind'),
        'action': result.get('action') or args.get('action'),
        'title': result.get('title'),
        'pmcid': result.get('pmcid'),
        'source_url': result.get('source_url'),
        'evidence_class': item['evidence_class'],
        'tool_status': result.get('status'),
        'origin_peer': item.get('origin_peer'),
        'original_tool_id': item['original_tool_id'],
        'pending_worker_interpretation': bool(item.get('pending_worker_interpretation', False)),
        'not_a_new_tool_execution': True,
        'not_scientifically_certified': True,
    }


def inherited_catalog(j, state, mode, *, query='', offset=0, limit=12):
    if mode != 'INFORMED':
        return {'status':'REJECTED','error_code':'FRESH_HISTORICAL_EVIDENCE_BLOCKED'}
    if (not isinstance(query,str) or len(query)>200 or not isinstance(offset,int)
            or isinstance(offset,bool) or offset<0 or not isinstance(limit,int)
            or isinstance(limit,bool) or not 1<=limit<=30):
        return {'status':'REJECTED','error_code':'INVALID_EVIDENCE_CATALOG_QUERY'}
    q=query.casefold().strip()
    matches=[]
    for sid in sorted(state.sources):
        data=archived_record(j,state,sid)
        if data is None:continue
        summary=archive_summary(sid,data)
        terms=(' '.join(str(v or '') for v in summary.values())).casefold()
        if not q or q in terms:matches.append(summary)
    page=matches[offset:offset+limit]
    return {'status':'DELIVERED','source_records':page,
            'total_matches':len(matches),
            'next_offset':offset+len(page) if offset+len(page)<len(matches) else None,
            'index_is_metadata_not_scientific_evidence':True,
            'use_source_lookup_for_exact_archived_content':True,
            'no_historical_source_exposure_to_fresh':True}


def inherited_read(j,state,sid,*,offset=0,limit=12000):
    data=archived_record(j,state,sid)
    if data is None:
        return None
    # Read the *verbatim archived payload*, not a fabricated summary of its science.
    # Pagination is needed for long original full-text and calculation records.
    raw=json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':'))
    if (not isinstance(offset,int) or isinstance(offset,bool) or offset<0
            or not isinstance(limit,int) or isinstance(limit,bool) or not 1<=limit<=16000):
        return {'status':'REJECTED','error_code':'INVALID_INHERITED_READ_PAGINATION'}
    return {'id':sid,'kind':'EXTERNAL_AUDIT','encoding':'canonical_json_text_chunk',
            'text':raw[offset:offset+limit],
            'total_chars':len(raw),'offset':offset,
            'next_offset':offset+limit if offset+limit<len(raw) else None,
            'provenance_verification':'IMMUTABLE_CONTENT_ADDRESSED_ARCHIVE',
            'not_an_independent_tool_execution':True,
            'scientific_certification':False}


def inherited_inventory(j,state,mode='INFORMED'):
    if mode != 'INFORMED':
        return {'readable_inherited_source_count':0,
                'historical_records_excluded_from_fresh':True}
    by_class=Counter()
    pending=0
    for sid in state.sources:
        item=archived_record(j,state,sid)
        if item is not None:
            by_class[item['evidence_class']]+=1
            if item.get('pending_worker_interpretation'):pending+=1
    return {'readable_inherited_source_count':sum(by_class.values()),
            'pending_prior_worker_interpretation_count':pending,
            'by_evidence_class':dict(by_class),
            'discovery_route':'source_catalog (query,offset,limit)',
            'read_route':'source_lookup (source_ids,offset,limit)',
            'historical_not_reexecuted_or_certified':True}


def uninterpreted_last_tool_feedback(j, state):
    """Identify only feedback that is last in a Work's Journal step sequence.

    A later Worker-authored MODEL_RESPONSE means that step is no longer pending;
    no claim is made that the model scientifically understood the result.
    """
    pending=[]
    for wid,w in state.work.items():
        if not w.get('steps') or w['steps'][-1]['kind']!='TOOL_RESULT':continue
        step=w['steps'][-1]
        payload=json.loads(j.raw(step['raw_blob']))
        tool_id=payload.get('tool_id')
        recorded=state.tool_results.get(tool_id)
        if recorded is None or recorded.get('work_id')!=wid:
            raise ValueError('PENDING_TOOL_RECORD_MISMATCH:'+str(wid))
        req=json.loads(j.raw(recorded['request_blob']))
        result=json.loads(j.raw(recorded['result_blob']))
        args=req.get('arguments',{}) if isinstance(req,dict) else {}
        if not isinstance(args,dict):args={}
        pending.append({
            'work_id':wid,'original_work_status':w['status'],
            'tool_id':tool_id,'tool_kind':req.get('kind'),
            'action':result.get('action') or args.get('action'),
            'tool_status':result.get('status'),'evidence_class':result.get('evidence_class'),
            'request_blob_sha256':recorded['request_blob'],
            'result_blob_sha256':recorded['result_blob'],
            'awaits_worker_interpretation_at_checkpoint':True,
            'not_a_scientific_negative_or_result':True,
        })
    return pending
