#!/usr/bin/env python3
"""Derive the independent science audit packet from the provided G13 exported report.

Does not assert an unregistered model-authored asset as Journal-published.
"""
from __future__ import annotations
import json,hashlib,sys,pathlib
report=json.loads(pathlib.Path(sys.argv[1]).read_text())
work={w['id']:w for w in report['works']}
w=work['W_develop_finite_exposure_adversarial_model_001']
tool=next(x['science'] for x in w['recent_steps'] if x['kind']=='TOOL_RESULT')
model=next(x['science'] for x in w['recent_steps'] if x['kind']=='MODEL_RESPONSE' and x['step']==2)
code=json.loads(model['text'])['tool_request']['arguments']['code']
code_hash=hashlib.sha256(code.encode()).hexdigest()
assert tool['result']['code_sha256']==code_hash
assert tool['result']['status']=='EXECUTED' and tool['result']['exit_code']==0
assert tool['tool_id']=='TOOL_W_develop_finite_exposure_adversarial_model_001_00002'
redox=work['W_develop_selective_intervention_boundary_001']
redox_raw=json.loads(next(x['science'] for x in redox['recent_steps'] if x['kind']=='MODEL_RESPONSE' and x['step']==20)['text'])
assert redox_raw['next_action']=='RETURN' and len(redox_raw.get('assets',[]))==2
assert any(x['science'].get('status')=='PARTIALLY_ACCEPTED' for x in redox['recent_steps'] if x['kind']=='OUTPUT_VALIDATION')
check=json.loads((pathlib.Path(__file__).parent/'INDEPENDENT_MC_CHECK.json').read_text())
packet={
 'schema':'EXTERNAL_SCIENTIFIC_PEER_FEEDBACK_V1',
 'author':'ChatGPT external independent computation and reading of user supplied G13 export',
 'classification':'INDEPENDENT_ANALYTICAL_AND_NUMERICAL_CHECK_NOT_PRIMARY_SERS_EVIDENCE',
 'not_a_journal_tool_execution':True,
 'not_a_model_generated_work_asset':True,
 'does_not_certify_novelty_or_level_ii':True,
 'source_report':'G13_LEVEL2_SCIENCE_REVIEW.json (operator supplied, snapshot 1268 events)',
 'scope':'Only finite-exposure INFORMED Work and related redox manuscript receipt; no control of FRESH researcher',
 'target_work_id':w['id'],
 'target_step_number':4,
 'original_calculation':{
  'tool_id':tool['tool_id'],
  'model_source_step':2,
  'tool_result_step':3,
  'code_sha256':code_hash,
  'result_status':'EXECUTED',
  'science_interpretation':'Original execution was real, but computational comparison did not satisfy its claimed matched covariance contract.'},
 'findings':[
  {'id':'F1','severity':'ERROR','finding':'Symmetric CTMC transition probability should be (1-exp(-dt/tau))/2 for autocorrelation tau, but executed code uses 1-exp(-2dt/tau). For dt=0.005 s and tau=0.1 s, it uses 0.09516258 instead of 0.02438529 and yields effective correlation time about 0.02368 s.',
   'required_validation':'Check simulated mean and shot-noise-corrected second factorial cumulant against analytic rate^2 contrast^2 2 tau[T-tau(1-exp(-T/tau))] before claiming covariance matching.'},
  {'id':'F2','severity':'INVALID_COMPARISON','finding':'For rate=1000/s, contrast=0.3, tau=T=0.1 s, the reported Telegraph K2^F=328.08 and Gaussian K2^F=663.48 are not covariance matched. Analytic intended K2^F=662.183. Independent event-driven Telegraph simulation reproduces this intended value (within sampling variability).',
   'required_validation':'Recompute comparison with true matched K2 and preregistered measurement model.'},
  {'id':'F3','severity':'LIMITATION','finding':'Gaussian intensity clipped at zero changes stationary mean/covariance and higher-order structure (particularly contrast=0.6); clipping is a property of that null, not evidence for a discrete mechanism.',
   'required_validation':'Use a positive continuous null with explicit covariance properties.'},
  {'id':'F4','severity':'ADVERSARIAL_NULL','finding':'A continuous bounded Jacobi diffusion dY=-(Y/tau)dt+sqrt((1-Y^2)/(a*tau))dW with stationary density proportional to (1-Y^2)^(a-1), normalized Z=sqrt(2a+1)Y, has exactly mean zero, variance one and covariance exp(-|t|/tau). rate*(1+contrast*Z) is positive when contrast*sqrt(2a+1)<1. At a=0.2 and contrast=0.6 the relative intensity minimum is 0.2901. It matches Telegraph mean and covariance exactly while having continuous trajectories.',
   'required_validation':'Challenge the high-order statistic using this or another physically bounded continuous null, not only clipped Gaussian OU.'},
  {'id':'F5','severity':'POWER_NOT_YET_DEMONSTRATED','finding':'Reported standardized separation combines between-repetition SDs; it is not empirical size-controlled power. The simulated mean/moment estimators also exhibit finite-sample bias and no declared valid size-calibrated decision rule.',
   'required_validation':'After fixing model equivalence, define independent train/test simulation, null calibration, alpha threshold and power, including finite-sample estimator bias.'},
  {'id':'F6','severity':'SCOPE','finding':'A telegraph-vs-continuous statistical discriminator is not by itself a novel SERS physical mechanism; Level II still requires a physical causal proposal, realistic domain and distinct prediction vs matched strong nulls.',
   'required_validation':'Decide autonomously whether continuing this statistical Work materially advances a concrete mechanistic hypothesis.'}
 ],
 'independent_checks':check,
 'redox_unregistered_candidate_notice':{
  'worker_id':'W_develop_selective_intervention_boundary_001',
  'model_response_step':20,
  'candidate_ids':[a['id'] for a in redox_raw['assets']],
  'status':'MODEL_AUTHORED_RAW_TEXT_ONLY_REJECTED_METADATA_NOT_REGISTERED_AS_ASSET',
  'validation_rejection':'BAD_ASSET_PARENTS',
  'parent_id_example':{'pinned_parent':'A_CARRY_b388fefbe6e025044c47dd9','model_emitted':'A_CARRY_b388fefbe6e025044c47dd93'},
  'scientific_context':'The proposed redox-gated picocavity is a conditional three-channel hypothesis (redox reporter, SERS kinetic transition, and geometry-sensitive optical channel); lacks bounded nuisance parameters, demonstrated independent reporter and prior-art novelty.',
  'not_promoted_to_asset':True,
  'do_not_silently_correct_old_model_or_journal':True},
 'instructions_to_researcher':'Treat all findings as a contestable external science audit, not certified fact. Examine the mathematics and actual tool output, correct or rebut with a documented calculation. Choose next actions independently. Do not force the redox candidate into this finite-exposure Work; it remains a separate possible opportunity for later Population review.'
}
out=pathlib.Path(__file__).parent/'SCIENTIFIC_AUDIT_PACKET.json'
out.write_text(json.dumps(packet,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
print(out, len(out.read_bytes()),hashlib.sha256(out.read_bytes()).hexdigest())
