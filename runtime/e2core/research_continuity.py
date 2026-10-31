"""Native, read-only research-opportunity and typed-lineage contract.

A rejected MODEL proposal is NOT an accepted scientific asset, literature
source, successful tool result, or a scientific verdict. Journal events remain
append-only. Only Controller-selected, validated opportunity records can enter
an INFORMED Work. No implicit scientific retry is performed here.

The implementation derives live opportunity records from existing Journal
blobs and can read one separately pinned, immutable external archive at the
POPULATION stage. PEER research never receives that external archive.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path

VERSION = 'NATIVE_RESEARCH_CONTINUITY_V1'
PIN_NAME = 'SCIENTIFIC_OPPORTUNITY_ARCHIVE_PIN.json'
ARCHIVE_SCHEMA = 'M15_UNREGISTERED_OPPORTUNITY_ARCHIVE_V1'
MAX_ARCHIVE_BYTES = 8_000_000
MAX_HANDOFF_BYTES = 25_000
MAX_INDEX_ITEMS = 8

class ContinuityError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf8')


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else canonical(value)).hexdigest()


def _ids(value, label, min_count=0):
    if (not isinstance(value, list) or len(value) < min_count
        or any(not isinstance(x, str) or not x for x in value)
        or len(value) != len(set(value))):
        raise ContinuityError('CONTINUITY_INVALID_'+label)
    return value


def normalize_problem(proposal, state, *, mode, origin_work_id=None, allowed_assets=None):
    """Accept typed PARENTS vs MOTIVATION, never guess or repair wrong IDs.

    Legacy proposals are not changed. The typed contract is optional; E2's
    existing PROBLEM_CREATED parents still denotes only Problem IDs.
    """
    if not isinstance(proposal, dict):
        raise ContinuityError('CONTINUITY_PROBLEM_NOT_OBJECT')
    if 'parent_problem_ids' not in proposal:
        return copy.deepcopy(proposal)
    parents = _ids(proposal['parent_problem_ids'], 'PARENT_PROBLEM_IDS', 1)
    motivating = _ids(proposal.get('motivating_asset_ids', []), 'MOTIVATING_ASSET_IDS')
    if 'parents' in proposal and proposal['parents'] != parents:
        raise ContinuityError('CONTINUITY_CONFLICTING_LEGACY_PARENTS')
    if any(x not in state.problems for x in parents):
        raise ContinuityError('CONTINUITY_UNKNOWN_PARENT_PROBLEM')
    if any(x not in state.assets for x in motivating):
        raise ContinuityError('CONTINUITY_UNKNOWN_MOTIVATING_ASSET')
    if mode not in ('FRESH', 'INFORMED', 'CONTROLLER'):
        raise ContinuityError('CONTINUITY_UNKNOWN_RESEARCH_MODE')
    # FRESH may cite scientific outputs it created itself, but never inherited
    # assets. E2's FRESH Work has no asset_input_ids, only own published IDs.
    if mode == 'FRESH' and any(x not in (allowed_assets or set()) for x in motivating):
        raise ContinuityError('CONTINUITY_FRESH_MOTIVATION_FORBIDDEN')
    if mode == 'INFORMED' and any(x not in (allowed_assets or set()) for x in motivating):
        raise ContinuityError('CONTINUITY_UNAUTHORIZED_MOTIVATION')
    result = copy.deepcopy(proposal)
    result['parents'] = list(parents)
    result['continuity_contract_version'] = VERSION
    if mode != 'CONTROLLER':
        result['continuity_origin_work_id'] = origin_work_id
    return result


def check_typed_problem(payload, state):
    if 'parent_problem_ids' not in payload:
        return
    who = payload.get('continuity_origin_work_id')
    if who is None:
        mode = 'CONTROLLER'; allowed = set()
    else:
        if who not in state.work:
            raise ContinuityError('CONTINUITY_PROBLEM_ORIGIN_WORK_UNKNOWN')
        work = state.work[who]
        mode = work['mode']
        allowed = set(work.get('asset_input_ids', [])) | set(work.get('published', []))
    result = normalize_problem(payload, state, mode=mode,
                               origin_work_id=who, allowed_assets=allowed)
    if (payload.get('parents') != result['parents']
        or payload.get('continuity_contract_version') != VERSION):
        raise ContinuityError('CONTINUITY_TYPED_PROBLEM_RECORD_MISMATCH')


def _parse_saved_worker(text):
    # Direct import is safe: the parser has no side effects and this function is
    # called only to derive an already rejected proposal, never to re-execute it.
    from .worker_json import parse_worker_response
    obj, _ = parse_worker_response(text)
    return obj if isinstance(obj, dict) else {}


def extract_rejected(work_id, steps, read_blob):
    """Derive proposals ONLY from actual OUTPUT_VALIDATION index rejections."""
    records = {}
    prior = None
    for step in steps:
        if step.get('kind') == 'MODEL_RESPONSE':
            prior = step
            continue
        if step.get('kind') != 'OUTPUT_VALIDATION' or prior is None:
            continue
        try:
            validation = json.loads(read_blob(step['raw_blob']))
            response = json.loads(read_blob(prior['raw_blob']))
            proposal = _parse_saved_worker(response.get('text', ''))
        except (KeyError, TypeError, ValueError):
            continue
        rejected = validation.get('rejected', [])
        if not isinstance(rejected, list):
            continue
        for kind, field in (('PROBLEM','new_problems'), ('ASSET','assets')):
            entries = proposal.get(field, [])
            if not isinstance(entries, list):
                continue
            by_index = {}
            for item in rejected:
                if not isinstance(item, dict) or item.get('kind') != kind:
                    continue
                index = item.get('index')
                if type(index) is int and 0 <= index < len(entries):
                    by_index.setdefault(index, []).append(str(item.get('error', 'UNKNOWN')))
            for index, reasons in by_index.items():
                original = entries[index]
                if not isinstance(original, dict):
                    continue
                ident = 'OPP_'+digest({'work':work_id,'response_step':prior['step'],
                    'kind':kind,'index':index,'response_blob':prior['raw_blob']})[:24]
                item = {
                    'opportunity_id': ident,
                    'status': 'UNREGISTERED_PROPOSAL_REJECTED',
                    'kind': kind,
                    'original_id': original.get('id'),
                    'original_submission': copy.deepcopy(original),
                    'validation_errors': list(dict.fromkeys(reasons)),
                    'origin': {'work_id': work_id, 'model_response_step': prior['step'],
                        'response_blob_sha256': prior['raw_blob'],
                        'validation_blob_sha256': step['raw_blob'],
                        'validation_step': step['step']},
                    'science_certification': False,
                    'not_an_asset': True,
                    'not_a_primary_source': True,
                }
                if ident in records and records[ident] != item:
                    raise ContinuityError('CONTINUITY_LIVE_OPPORTUNITY_COLLISION')
                records[ident] = item
    return records


def live_opportunities(j, state=None):
    s = j.verify() if state is None else state
    result = {}
    for wid, work in s.work.items():
        for ident, record in extract_rejected(wid, work.get('steps', []), j.raw).items():
            if ident in result and result[ident] != record:
                raise ContinuityError('CONTINUITY_LIVE_OPPORTUNITY_COLLISION')
            result[ident] = record
    return result


def _external_pin(journal_root):
    """Only a CYCLE_xxx/POPULATION research ROOT may see an external archive."""
    root = Path(journal_root).resolve()
    if root.name != 'POPULATION' or not root.parent.name.startswith('CYCLE_'):
        return None
    return root.parent.parent / PIN_NAME


def validate_archive(path):
    p = Path(path).expanduser().resolve(strict=True)
    data = p.read_bytes()
    if len(data) > MAX_ARCHIVE_BYTES:
        raise ContinuityError('CONTINUITY_ARCHIVE_TOO_LARGE')
    doc = json.loads(data)
    if (doc.get('schema') != ARCHIVE_SCHEMA
        or doc.get('source_kind') != 'DERIVED_G14_TRACE_NOT_E2_JOURNAL_NOT_PRIMARY'
        or doc.get('science_certification') is not False):
        raise ContinuityError('CONTINUITY_ARCHIVE_BAD_PROVENANCE')
    entries = doc.get('opportunities')
    if (not isinstance(entries, dict) or doc.get('record_count') != len(entries)
        or doc.get('entry_index_sha256') != digest(entries)):
        raise ContinuityError('CONTINUITY_ARCHIVE_BAD_INDEX')
    for ident, entry in entries.items():
        validate_record(entry)
        if ident != entry['opportunity_id']:
            raise ContinuityError('CONTINUITY_ARCHIVE_BAD_ID')
    return entries, digest(data)


def pin_archive(experiment, archive):
    """Create a one-time immutable archive pointer outside any E2 Journal.

    The operator configures evidence availability, NOT which hypothesis the
    scientists must pursue. Never alter a pre-existing pin or journal.
    """
    exp = Path(experiment).expanduser().resolve(strict=True)
    archive_path = Path(archive).expanduser().resolve(strict=True)
    if not exp.is_dir() or not (exp/'persistent.json').exists():
        raise ContinuityError('CONTINUITY_NOT_PERSISTENT_EXPERIMENT')
    if not (exp/'STOP_REQUESTED').is_file():
        raise ContinuityError('CONTINUITY_CONFIG_ONLY_WHILE_EXPERIMENT_STOPPED')
    if os.environ.get('FAKG_RESEARCH_ALLOW_PAID')=='YES':
        raise ContinuityError('CONTINUITY_PIN_REQUIRES_NO_PAID_EXECUTION')
    entries, archive_sha = validate_archive(archive_path)
    pin = {'schema': VERSION, 'archive_path': str(archive_path),
           'archive_sha256': archive_sha, 'index_sha256': digest(entries),
           'entries': len(entries), 'science_certification': False,
           'scope': 'POPULATION_STAGE_ONLY', 'source_is_not_primary': True}
    target = exp/PIN_NAME
    with target.open('xb') as f:
        f.write(canonical(pin)+b'\n')
    return pin


def archived_opportunities(journal_root):
    pin_path = _external_pin(journal_root)
    if pin_path is None or not pin_path.exists():
        return {}
    pin = json.loads(pin_path.read_bytes())
    if (pin.get('schema') != VERSION
        or pin.get('scope') != 'POPULATION_STAGE_ONLY'
        or pin.get('source_is_not_primary') is not True
        or pin.get('science_certification') is not False):
        raise ContinuityError('CONTINUITY_PIN_BAD_SCHEMA')
    path = Path(pin['archive_path']).resolve(strict=True)
    entries, observed_sha = validate_archive(path)
    if (observed_sha != pin.get('archive_sha256')
        or digest(entries) != pin.get('index_sha256')
        or len(entries) != pin.get('entries')):
        raise ContinuityError('CONTINUITY_ARCHIVE_PIN_MISMATCH')
    return entries


def validate_record(entry):
    if (not isinstance(entry, dict)
        or not isinstance(entry.get('opportunity_id'), str)
        or not entry['opportunity_id']
        or entry.get('status') != 'UNREGISTERED_PROPOSAL_REJECTED'
        or entry.get('science_certification') is not False
        or entry.get('not_an_asset') is not True
        or entry.get('not_a_primary_source') is not True
        or entry.get('kind') not in ('PROBLEM', 'ASSET')
        or not isinstance(entry.get('original_submission'), dict)
        or not isinstance(entry.get('validation_errors'), list)
        or not entry['validation_errors']
        or not isinstance(entry.get('origin'), dict)):
        raise ContinuityError('CONTINUITY_INVALID_REJECTED_PROPOSAL')
    return entry


def opportunities_for_journal(j):
    # Peers never see imported previous-generation rejected suggestions.
    # These are exposed only after independent researchers are pooled.
    result = archived_opportunities(j.root)
    if _external_pin(j.root) is not None:
        for ident, record in j.verify().carried_opportunities.items():
            validate_record(record)
            if ident in result and result[ident] != record:
                raise ContinuityError('CONTINUITY_CARRIED_ARCHIVE_COLLISION')
            result[ident] = copy.deepcopy(record)
    for ident, record in live_opportunities(j).items():
        if ident in result and result[ident] != record:
            raise ContinuityError('CONTINUITY_ARCHIVE_LIVE_COLLISION')
        result[ident] = record
    return result


def concise_index(index, *, max_items=MAX_INDEX_ITEMS):
    records = []
    for ident, entry in sorted(index.items()):
        validate_record(entry)
        original = entry['original_submission']
        summary = original.get('claim') or original.get('question') or ''
        records.append({'opportunity_id': ident,'kind':entry['kind'],
            'original_id':entry.get('original_id'),
            'origin_work_id':entry['origin'].get('work_id'),
            'summary': str(summary)[:320],
            'rejection_reasons':entry['validation_errors'],
            'registered':False,'scientific_certification':False})
    # A bounded view is contextual headroom, never deletion from the index.
    return {'count':len(index), 'entries':records[-max_items:],
            'catalog':[{'opportunity_id':r['opportunity_id'],
                        'original_id':r['original_id'], 'kind':r['kind']}
                       for r in records],
            'index_sha256':digest(index),
            'truncated':len(records)>max_items,
            'not_scientific_assets':True, 'not_primary_evidence':True,
            'controller_may_ignore':True}


def validate_handoff(ids, mode, index):
    ids = _ids(ids, 'OPPORTUNITY_IDS')
    if mode not in ('FRESH','INFORMED'):
        raise ContinuityError('CONTINUITY_INVALID_WORK_MODE')
    if mode == 'FRESH' and ids:
        raise ContinuityError('CONTINUITY_FRESH_OPPORTUNITY_CONTAMINATION')
    if any(ident not in index for ident in ids):
        raise ContinuityError('CONTINUITY_UNKNOWN_OPPORTUNITY')
    return ids


def pin_work_handoff(work, index):
    """Seal only explicit selected opportunities inside new Work event payload."""
    if not isinstance(work, dict):
        raise ContinuityError('CONTINUITY_WORK_NOT_OBJECT')
    ids = validate_handoff(work.get('opportunity_input_ids', []), work.get('mode'), index)
    if 'opportunity_handoff_records' in work:
        raise ContinuityError('CONTINUITY_CONTROLLER_MUST_NOT_AUTHENTICATE_OWN_RECORDS')
    result = copy.deepcopy(work)
    if not ids:
        return result
    records = [copy.deepcopy(index[i]) for i in ids]
    if len(canonical(records)) > MAX_HANDOFF_BYTES:
        raise ContinuityError('CONTINUITY_HANDOFF_TOO_LARGE')
    result['opportunity_handoff_records'] = records
    result['opportunity_handoff_digest'] = digest(records)
    result['continuity_contract_version'] = VERSION
    return result


def check_work_handoff(work):
    """Replay-only validation of immutable records. No external file needed."""
    if not isinstance(work, dict):
        raise ContinuityError('CONTINUITY_WORK_NOT_OBJECT')
    ids = _ids(work.get('opportunity_input_ids', []), 'OPPORTUNITY_IDS')
    if work.get('mode') == 'FRESH' and ids:
        raise ContinuityError('CONTINUITY_FRESH_OPPORTUNITY_CONTAMINATION')
    records = work.get('opportunity_handoff_records')
    if not ids:
        if records is not None or 'opportunity_handoff_digest' in work:
            raise ContinuityError('CONTINUITY_UNREQUESTED_HANDOFF_RECORDS')
        return
    if (work.get('mode') != 'INFORMED' or not isinstance(records, list)
        or len(records) != len(ids) or len(canonical(records)) > MAX_HANDOFF_BYTES):
        raise ContinuityError('CONTINUITY_BAD_WORK_HANDOFF')
    for ident, record in zip(ids, records):
        validate_record(record)
        if record['opportunity_id'] != ident:
            raise ContinuityError('CONTINUITY_HANDOFF_ID_MISMATCH')
    if (work.get('continuity_contract_version') != VERSION
        or work.get('opportunity_handoff_digest') != digest(records)):
        raise ContinuityError('CONTINUITY_HANDOFF_DIGEST_MISMATCH')


def worker_handoff(work):
    check_work_handoff(work)
    return {'scope':'EXPLICIT_MODEL_SELECTED_PREVIOUSLY_REJECTED_PROPOSALS',
        'records':copy.deepcopy(work.get('opportunity_handoff_records', [])),
        'not_scientific_assets':True, 'not_primary_evidence':True,
        'instruction':'Prior rejected MODEL suggestions only; independently test, revise, or reject; do not cite as verified measurements.'}
