"""Worker-response serialization boundary, independent of scientific judgement.

Accept one complete JSON dictionary or a whitespace-separated repetition of the
*same* complete dictionary. Never choose between distinct authored research
outputs. The original model text is stored by Engine without modification.

This contract is used only by Worker; Controller/advisory parsing remains unchanged.
Historical journals/finished work are never rewritten or reinterpreted here.
"""
from __future__ import annotations
import hashlib
import json

MAX_WORKER_CONTENT_CHARS = 1_000_000
MAX_IDENTICAL_COPIES = 4


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('DUPLICATE_JSON_OBJECT_KEY:' + key)
        result[key] = value
    return result


def _reject_constant(name):
    raise ValueError('NON_JSON_CONSTANT:' + name)


def _canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(',', ':')).encode('utf-8')


def _complete_documents(text):
    """Return all complete top-level dicts, or None; no repair/partial parsing."""
    if not isinstance(text, str) or not text or len(text) > MAX_WORKER_CONTENT_CHARS:
        return None
    decoder = json.JSONDecoder(object_pairs_hook=_unique_pairs,
                               parse_constant=_reject_constant)
    pos = 0
    docs = []
    while pos < len(text):
        while pos < len(text) and text[pos].isspace():
            pos += 1
        if pos >= len(text):
            break
        try:
            obj, end = decoder.raw_decode(text, pos)
        except (ValueError, TypeError, json.JSONDecodeError):
            return None
        if not isinstance(obj, dict) or end <= pos:
            return None
        docs.append(obj)
        if len(docs) > MAX_IDENTICAL_COPIES:
            return None
        pos = end
    return docs or None


def parse_worker_response(text, legacy_single_parser):
    """Return (object or None, non-scientific audit metadata).

    The existing single-envelope parser is a compatibility fallback ONLY when
    no clean multi-document stream was found. Full JSON with duplicate keys or
    nonstandard constants does not bypass strict validation through fallback.
    Raw output is NEVER changed by this function.
    """
    documents = _complete_documents(text)
    if documents is not None:
        hashes = [hashlib.sha256(_canonical(item)).hexdigest() for item in documents]
        if len(documents) == 1:
            return documents[0], {'status': 'SINGLE_JSON',
                                  'document_count': 1,
                                  'canonical_sha256': hashes[0]}
        if len(set(hashes)) == 1:
            return documents[0], {'status': 'IDENTICAL_DUPLICATE_COLLAPSED',
                                  'document_count': len(documents),
                                  'canonical_sha256': hashes[0]}
        return None, {'status': 'DISTINCT_MULTIPLE_JSON_REJECTED',
                      'document_count': len(documents),
                      'canonical_sha256': None}

    if not isinstance(text, str) or len(text) > MAX_WORKER_CONTENT_CHARS:
        return None, {'status': 'INVALID_FORMAT', 'document_count': 0}

    # A fully formed JSON object that strict parsing rejects (e.g. duplicate
    # keys or NaN) must not be accepted by the older permissive parser.
    try:
        entire_json = json.loads(text)
    except (ValueError, TypeError):
        entire_json = None
    if entire_json is not None:
        return None, {'status': 'INVALID_JSON_OBJECT_CONTRACT', 'document_count': 0}

    # Preserve legacy single-envelope tolerance for preambles/format wrappers;
    # do not make this the general rule for multiple complete JSON documents.
    parsed = legacy_single_parser(text)
    if isinstance(parsed, dict):
        return parsed, {'status': 'LEGACY_SINGLE_ENVELOPE', 'document_count': 1}
    return None, {'status': 'INVALID_FORMAT', 'document_count': 0}
