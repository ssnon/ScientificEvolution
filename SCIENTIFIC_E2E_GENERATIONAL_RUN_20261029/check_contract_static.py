#!/usr/bin/env python3
"""Offline, no repository imports and no simulated science."""
import ast
from pathlib import Path
import subprocess
import sys
p=Path(__file__).with_name('generational_run.py')
s=p.read_text(encoding='utf-8')
a=ast.parse(s)
assert {'init','run-fresh','integrate','run-syn','audit','preflight'} <= set(
    node.value for node in ast.walk(a) if isinstance(node,ast.Constant) and isinstance(node.value,str))
assert 'transfer_isolated_fresh' in s
assert 'v4.runtime()' in s and 'v3.v3_runtime()' in s
assert 'src.verify()' in s
assert 'FEEDBACK_PREPARE_MANIFEST.json' in s
assert 'SRC_INHERITED_TOOL_' in s
assert 'fresh_serialized_requests_checked' in s
assert 'NEW_UNCERTAIN_CALL_STOP_AND_REVIEW' in s
q=subprocess.run([sys.executable,str(p),'--help'],capture_output=True,text=True,check=True)
assert 'run-fresh' in q.stdout and 'run-syn' in q.stdout
print('STATIC_CONTRACT_CHECK_OK: no paid calls or scientific simulations')
