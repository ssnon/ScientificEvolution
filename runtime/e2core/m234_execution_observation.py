"""M23.4 observational classification of sandbox execution vs scientific output.

This module does NOT validate mathematical correctness, reinterpret a legacy
Journal, mandate a computation, or choose a scientific hypothesis. The model's
`result.status` is data and cannot certify that calculations were performed.
"""
from __future__ import annotations


NONCOMPUTATION_LABELS = frozenset({
    'not_executed', 'not_run', 'not_performed', 'planned_only',
})


def inspect_python_execution(request, response):
    """Summarize recorded Python execution without making a scientific verdict.

    Returned labels describe tool/process observations and model-authored
    claims only. The raw request/response are not rewritten or normalized.
    """
    if not isinstance(request, dict) or request.get('kind') != 'python_science':
        return None
    response = response if isinstance(response, dict) else {}
    execution_status = response.get('status')
    declared = response.get('result')
    claim = declared.get('status') if isinstance(declared, dict) else None
    self_reports_no_computation = (
        isinstance(claim, str) and claim.strip().lower() in NONCOMPUTATION_LABELS
    )
    if execution_status != 'EXECUTED':
        observation = 'NO_SUCCESSFUL_SANDBOX_EXECUTION_RECORDED'
    elif self_reports_no_computation:
        observation = 'SANDBOX_EXECUTED_MODEL_DECLARED_NO_COMPUTATION'
    else:
        observation = 'SANDBOX_EXECUTED_SCIENTIFIC_CONTENT_UNVERIFIED'
    return {
        'observation': observation,
        'sandbox_execution_status': execution_status,
        'model_result_status': claim,
        'model_declared_noncomputation': self_reports_no_computation,
        'scientific_computation_validated': False,
        'interpretation_boundary': (
            'Sandbox execution is not scientific validation. Model-authored '
            'result fields are claims, not independent evidence that a '
            'simulation, numerical benchmark, or derivation was performed.'
        ),
    }
