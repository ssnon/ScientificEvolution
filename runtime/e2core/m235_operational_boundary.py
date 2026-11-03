"""M23.5: separate development budget pauses from scientific dispositions.

This only interprets exact operational sentinel strings emitted by the native
cost guard. It cannot allocate funding, issue paid calls, or certify research.
"""
from __future__ import annotations

BUDGET_GUARD_ERROR = 'OPERATIONAL_DEVELOPMENT_BUDGET_REACHED_NO_NEW_CALL_INTENT'
BUDGET_PAUSE = 'OPERATIONAL_DEVELOPMENT_BUDGET_PAUSE'


def is_dev_budget_error(exception):
    return str(exception) == BUDGET_GUARD_ERROR


def is_dev_budget_pause(decisions):
    if not isinstance(decisions, list):
        return False
    for decision in decisions:
        if not isinstance(decision, dict):
            continue
        reason = decision.get('operational_pause')
        if reason in (BUDGET_PAUSE, 'WORKER_OR_CONTROLLER_RUNTIME_ERROR:' + BUDGET_GUARD_ERROR):
            return True
    return False
