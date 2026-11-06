"""Optional cross-root development *operational* budget using SQLite reservations.

No change to scientific disposition. No paid model calls here. The configured
limit is conservative, not a provider-billing guarantee: future actual cost is
unknown until a response is delivered. Keep an external API-key spending limit.
"""
from __future__ import annotations
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import time
from .core import EvidenceError

CONFIG_NAME = 'M232_DEV_BUDGET.json'
DATABASE_NAME = '.M232_DEV_BUDGET.sqlite3'


def _experiment_path(journal_root):
    p = Path(journal_root).expanduser().resolve()
    for candidate in (p, *p.parents):
        # Persistent Population uses persistent.json, whereas earlier autonomous
        # experiments use autonomous.json. Both are native experiment roots.
        if ((candidate / 'autonomous.json').is_file()
                or (candidate / 'persistent.json').is_file()):
            return candidate
    return None


def _config(exp):
    if exp is None:
        if os.getenv('M232_BUDGET_REQUIRED') == 'YES':
            raise EvidenceError('M232_BUDGET_REQUIRED_OUTSIDE_AUTONOMOUS_EXPERIMENT')
        return None
    path = exp / CONFIG_NAME
    if not path.is_file():
        if os.getenv('M232_BUDGET_REQUIRED') == 'YES':
            raise EvidenceError('M232_DEVELOPMENT_BUDGET_NOT_CONFIGURED')
        return None
    obj = json.loads(path.read_text(encoding='utf8'))
    if obj.get('protocol') != 'M232_DEVELOPMENT_BUDGET_V1':
        raise EvidenceError('M232_BUDGET_PROTOCOL_MISMATCH')
    cap = obj.get('limit_usd')
    if type(cap) not in (int, float) or not math.isfinite(cap) or cap <= 0:
        raise EvidenceError('M232_BAD_USD_BUDGET')
    rates = obj.get('model_rates_per_million_usd')
    if not isinstance(rates, dict) or not rates:
        raise EvidenceError('M232_MODEL_RATES_REQUIRED')
    for model, rate in rates.items():
        if not isinstance(model, str) or not isinstance(rate, dict):
            raise EvidenceError('M232_INVALID_MODEL_RATE')
        if any(type(rate.get(k)) not in (int, float) or not math.isfinite(rate[k]) or rate[k] <= 0
               for k in ('input', 'output')):
            raise EvidenceError('M232_INVALID_MODEL_RATE')
    return obj


def _connection(exp):
    c = sqlite3.connect(str(exp / DATABASE_NAME), timeout=30, isolation_level=None)
    c.execute('PRAGMA busy_timeout=30000')
    c.execute('CREATE TABLE IF NOT EXISTS calls (key TEXT PRIMARY KEY, journal_root TEXT NOT NULL, '
              'call_id TEXT NOT NULL, request_sha256 TEXT NOT NULL, model TEXT NOT NULL, '
              'state TEXT NOT NULL, reserved_usd REAL NOT NULL, actual_usd REAL, created REAL NOT NULL)')
    return c


def reserve_call(journal_root, ident, wire, model, max_tokens, mode):
    """Reserve estimated dollars before MODEL_CALL_INTENT. Returns receipt or None.

    A crashed or uncertain call *retains* its reservation until manual review.
    Do not infer billing success/failure from HTTP errors.
    """
    if mode == 'MOCK':
        return None
    exp = _experiment_path(journal_root)
    config = _config(exp)
    if config is None:
        return None
    if model not in config['model_rates_per_million_usd']:
        raise EvidenceError('M232_BUDGET_MODEL_RATE_UNKNOWN')
    rate = config['model_rates_per_million_usd'][model]
    # Conservative engineering estimate; an actual token count is unavailable.
    input_tokens = len(wire) / 2.0
    reserve = (input_tokens * rate['input'] + max_tokens * rate['output']) / 1_000_000.0
    reserve *= float(config.get('reserve_multiplier', 1.25))
    if not math.isfinite(reserve) or reserve <= 0:
        raise EvidenceError('M232_INVALID_BUDGET_RESERVATION')
    root = str(Path(journal_root).resolve())
    key = hashlib.sha256((root + '\n' + ident).encode('utf8')).hexdigest()
    reqsha = hashlib.sha256(wire).hexdigest()
    conn = _connection(exp)
    try:
        conn.execute('BEGIN IMMEDIATE')
        if conn.execute('SELECT 1 FROM calls WHERE key=?', (key,)).fetchone():
            raise EvidenceError('M232_EXISTING_BUDGET_RESERVATION_REQUIRES_RECONCILIATION')
        used = conn.execute('SELECT COALESCE(SUM(CASE WHEN state=? AND actual_usd IS NOT NULL '
                            'THEN actual_usd ELSE reserved_usd END), 0) FROM calls', ('SAVED',)).fetchone()[0]
        if used + reserve > config['limit_usd'] + 1e-10:
            raise EvidenceError('OPERATIONAL_DEVELOPMENT_BUDGET_REACHED_NO_NEW_CALL_INTENT')
        conn.execute('INSERT INTO calls VALUES (?,?,?,?,?,?,?,?,?)',
                     (key, root, ident, reqsha, model, 'RESERVED', reserve, None, time.time()))
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()
    return str(exp), key, reqsha


def settle_call(reservation, usage):
    """Only a provider-reported cost is authoritative. Otherwise retain reservation."""
    if reservation is None or not isinstance(usage, dict):
        return
    actual = usage.get('cost')
    if type(actual) not in (int, float) or not math.isfinite(actual) or actual < 0:
        return
    exp, key, _reqsha = reservation
    conn = _connection(Path(exp))
    try:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('SELECT state FROM calls WHERE key=?', (key,)).fetchone()
        if row is None or row[0] != 'RESERVED':
            raise EvidenceError('M232_BUDGET_SETTLEMENT_STATE_INVALID')
        conn.execute('UPDATE calls SET state=?, actual_usd=? WHERE key=?', ('SAVED', actual, key))
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def budget_report(experiment):
    exp = Path(experiment).expanduser().resolve()
    cfg = _config(exp)
    if cfg is None:
        return {'status': 'NOT_CONFIGURED'}
    conn = _connection(exp)
    try:
        rows = conn.execute('SELECT state, COUNT(*), SUM(reserved_usd), SUM(actual_usd) '
                            'FROM calls GROUP BY state').fetchall()
        total = conn.execute('SELECT COALESCE(SUM(CASE WHEN state=? AND actual_usd IS NOT NULL '
                             'THEN actual_usd ELSE reserved_usd END),0) FROM calls', ('SAVED',)).fetchone()[0]
    finally:
        conn.close()
    return {'status':'M232_OPERATIONAL_COST_LEDGER', 'limit_usd':cfg['limit_usd'],
            'charged_or_reserved_usd':round(total, 6),
            'remaining_estimated_usd':round(cfg['limit_usd']-total, 6),
            'states': {name: {'count':count,'reserved_usd':reserve,'actual_usd':actual}
                       for name,count,reserve,actual in rows},
            'note':'Estimates are not an absolute provider-side ceiling. Hold uncertain reservations.'}
