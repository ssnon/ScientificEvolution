"""M22: provenance-exact carry of rejected PEER Worker proposals, NOT accepted science.

Called only during preparation of a NEW generation's clean base from a verified
Population donor. It reads the exact original PEER Journal, never replays any
model/tool call, alters a PEER Journal, selects winners, or creates an Asset.
"""
from __future__ import annotations
import copy
import json

from .research_continuity import live_opportunities, validate_record, digest
from .worker_json import parse_worker_response
from .provider import content_from_wire


class PeerRejectedContinuityError(ValueError):
    pass


def _require(condition, code):
    if not condition:
        raise PeerRejectedContinuityError(code)


def _verify_worker_step_links(donor, state, sha):
    """Fail closed before deriving an opportunity index from Worker records.

    The legacy live_opportunities extractor intentionally tolerates malformed
    candidate text.  Crucially, it also tolerates a missing WORK_STEP blob while
    parsing a rejected proposal.  Such a missing/mismatched record must not
    silently mean "there were no rejected proposals" at a lineage boundary.

    We verify transport/linkage integrity, NOT the scientific correctness of an
    authored Worker statement or its rejected metadata.  Valid format-repair
    records need not contain a ``rejected`` array.
    """
    for wid, work in state.work.items():
        steps = work.get('steps', [])
        _require(isinstance(steps, list), 'M22_PEER_WORK_STEPS_INVALID')
        for position, step in enumerate(steps, 1):
            if step.get('kind') not in ('MODEL_RESPONSE', 'OUTPUT_VALIDATION'):
                continue
            link = step.get('raw_blob')
            _require(step.get('step') == position and isinstance(link, str) and
                     len(link) == 64 and all(c in '0123456789abcdef' for c in link),
                     'M22_PEER_STEP_LINK_INVALID')
            try:
                raw = donor.raw(link)
            except (OSError, KeyError, ValueError) as exc:
                raise PeerRejectedContinuityError(
                    'M22_PEER_STEP_BLOB_MISSING_OR_INVALID:' + wid) from exc
            _require(isinstance(raw, bytes) and sha(raw) == link,
                     'M22_PEER_STEP_BLOB_HASH_MISMATCH')
            try:
                payload = json.loads(raw)
            except (TypeError, ValueError) as exc:
                raise PeerRejectedContinuityError(
                    'M22_PEER_STEP_BLOB_NOT_JSON') from exc
            _require(isinstance(payload, dict), 'M22_PEER_STEP_PAYLOAD_NOT_OBJECT')
            if step['kind'] == 'MODEL_RESPONSE':
                _require(isinstance(payload.get('call_id'), str) and
                         isinstance(payload.get('text'), str),
                         'M22_PEER_MODEL_RESPONSE_SHAPE_INVALID')
            else:
                # A format-repair validation is a valid record even without
                # rejected proposal metadata.  MODEL_RESPONSE bytes cannot
                # masquerade as an OUTPUT_VALIDATION record.
                _require(isinstance(payload.get('status'), str) and
                         (payload.get('rejected') is None or
                          isinstance(payload.get('rejected'), list)),
                         'M22_PEER_VALIDATION_SHAPE_INVALID')


def collect_verified_peer_rejections(donor, state, peer_name, verified_head, *, sha, canon):
    """Return new, namespace-separated OPPORTUNITY_CARRIED records.

    An index rejection is NOT scientific falsification. The original authored
    proposal is included verbatim. Science prose is included if it fits a
    bounded explicit Worker handoff; otherwise the original SHA remains pinned.
    All primary bytes remain in the immutable original peer Journal.
    """
    _require(isinstance(peer_name,str) and peer_name and isinstance(verified_head,str)
             and len(verified_head)==64, 'M22_BAD_PEER_IDENTITY')
    _verify_worker_step_links(donor, state, sha)
    result={}
    for old_id, old in sorted(live_opportunities(donor, state).items()):
        validate_record(old)
        p=old['origin'];wid=p.get('work_id')
        work=state.work.get(wid)
        _require(work is not None, 'M22_PEER_OPPORTUNITY_WORK_MISSING')
        steps=work.get('steps',[])
        rn=p.get('model_response_step'); vn=p.get('validation_step')
        _require(type(rn) is int and type(vn) is int and
                 1 <= rn < vn <= len(steps), 'M22_PEER_OPPORTUNITY_STEP_INDEX_BAD')
        response_step=steps[rn-1]; validation_step=steps[vn-1]
        _require(response_step.get('kind')=='MODEL_RESPONSE' and
                 validation_step.get('kind')=='OUTPUT_VALIDATION' and
                 response_step.get('raw_blob')==p.get('response_blob_sha256') and
                 validation_step.get('raw_blob')==p.get('validation_blob_sha256'),
                 'M22_PEER_OPPORTUNITY_BLOB_LINK_BAD')
        response=json.loads(donor.raw(response_step['raw_blob']))
        validation=json.loads(donor.raw(validation_step['raw_blob']))
        cid=response.get('call_id');call=state.model_calls.get(cid)
        _require(bool(call) and call.get('state')=='SAVED' and
                 call.get('actor')=='WORKER' and call.get('work_id')==wid,
                 'M22_PEER_OPPORTUNITY_UNSAVED_OR_WRONG_ACTOR')
        _require(content_from_wire(donor.raw(call['response_blob']))==response.get('text'),
                 'M22_WORKER_STEP_DIFFERS_FROM_SAVED_PROVIDER_WIRE')
        parsed, format_audit=parse_worker_response(response.get('text'))
        _require(isinstance(parsed,dict) and isinstance(parsed.get('scientific_text'),str),
                 'M22_PEER_OPPORTUNITY_MODEL_BODY_NOT_PARSEABLE')
        field='assets' if old['kind']=='ASSET' else 'new_problems'
        _require(isinstance(parsed.get(field),list),
                 'M22_PEER_OPPORTUNITY_SUBMISSION_CHANGED')
        candidate_indices=[i for i,x in enumerate(parsed[field])
                           if x==old['original_submission'] and
                           old_id=='OPP_'+digest({'work':wid,'response_step':rn,
                               'kind':old['kind'],'index':i,
                               'response_blob':response_step['raw_blob']})[:24]]
        _require(len(candidate_indices)==1,
                 'M22_PEER_OPPORTUNITY_ORIGINAL_INDEX_MISMATCH')
        _require(any(x.get('index')==candidate_indices[0] and
                     x.get('kind')==old['kind'] and
                     x.get('error') in old['validation_errors']
                     for x in validation.get('rejected',[]) if isinstance(x,dict)),
                 'M22_PEER_OPPORTUNITY_REJECTION_NOT_VERIFIED')
        ident='OPP_'+sha(canon({'m22_peer':peer_name,'root':str(donor.root),
                                 'head':verified_head,'old':old_id}))[:24]
        item=copy.deepcopy(old)
        item['opportunity_id']=ident
        item['origin']={**item['origin'],
            'original_opportunity_id':old_id,'original_peer':peer_name,
            'original_peer_root':str(donor.root),
            'verified_original_peer_head_sha256':verified_head,
            'saved_worker_model_call_id':cid,
            'model_call_request_blob_sha256':call.get('request_blob'),
            'model_call_response_blob_sha256':call.get('response_blob'),
            'worker_format_audit':format_audit}
        item['unregistered_worker_science_text_sha256']=sha(parsed['scientific_text'].encode('utf-8'))
        item['original_scientific_text_is_model_authored_unreviewed']=True
        item['not_a_new_tool_execution']=True
        item['not_an_accepted_asset']=True
        # Prevent an exceptionally long draft from making explicit, bounded
        # handoff impossible. Do not discard or rewrite source material:
        # exact full authored text remains in the original Peer Journal.
        if len(parsed['scientific_text']) <= 8000:
            item['unregistered_worker_scientific_text']=parsed['scientific_text']
            item['unregistered_scientific_text_excerpt_only']=False
        else:
            item['unregistered_worker_scientific_text']=parsed['scientific_text'][:3000]
            item['unregistered_scientific_text_excerpt_only']=True
        validate_record(item)
        _require(ident not in result,'M22_PEER_OPPORTUNITY_ID_COLLISION')
        result[ident]=item
    return result
