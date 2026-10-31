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


def parse_worker_response(text, legacy_single_parser=None):
    """Parse an unambiguous full Worker response, preserving raw provider text.

    ``legacy_single_parser`` is retained for existing Engine call sites, but
    deliberately not called: it can accept a complete first JSON document even
    when a malformed second document or trailing garbage remains. The only
    legacy tolerance retained here is a *leading* non-JSON preamble before one
    complete strictly parsed dictionary with whitespace-only trailing content.
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

    rejected = {'status': 'INVALID_FORMAT', 'document_count': 0}
    if not isinstance(text, str) or not text or len(text) > MAX_WORKER_CONTENT_CHARS:
        return None, rejected

    # A preamble is permitted for backward compatibility, but only when the
    # response contains exactly one COMPLETE JSON object and nothing afterwards.
    # Inspect the FIRST opening brace, never scan ahead to cherry-pick another.
    first = text.find('{')
    if first <= 0 or not text[:first].strip():
        return None, rejected
    # Reject a JSON-looking or malformed envelope in the preamble itself.
    if any(ch in text[:first] for ch in ('}', '[', ']')):
        return None, rejected
    decoder = json.JSONDecoder(object_pairs_hook=_unique_pairs,
                               parse_constant=_reject_constant)
    try:
        obj, end = decoder.raw_decode(text, first)
    except (ValueError, TypeError, json.JSONDecodeError):
        return None, rejected
    if not isinstance(obj, dict) or text[end:].strip():
        return None, rejected
    return obj, {'status': 'LEGACY_SINGLE_ENVELOPE',
                 'document_count': 1,
                 'canonical_sha256': hashlib.sha256(_canonical(obj)).hexdigest()}
