#!/usr/bin/env python3
"""Independent, reproducible analytic and event-exact Monte Carlo check.

This does NOT establish mechanistic novelty, empirical SERS feasibility or power.
No network; no paid model calls; no Journal writes.
"""
from __future__ import annotations
import json, math, argparse
import numpy as np

def integrated_variance(rate, contrast, tau, exposure):
    return (rate*contrast)**2 * 2*tau*(exposure-tau*(-math.expm1(-exposure/tau)))

def event_exact_telegraph(rng,n,rate,contrast,tau,exposure):
    # A symmetric CTMC has jump hazard 1/(2*tau) in each state.
    # Integrate each constant-intensity sojourn EXACTLY in continuous time.
    total=np.empty(n,dtype=float)
    states=rng.choice((-1.0,1.0),size=n)
    for i in range(n):
        t=0.;acc=0.;state=states[i]
        while t<exposure:
            jump=rng.exponential(scale=2*tau)
            interval=min(jump,exposure-t)
            acc+=rate*(1+contrast*state)*interval
            t+=interval
            if jump<=interval and t<exposure: state=-state
        total[i]=acc
    return rng.poisson(total)

def jacobi_null_moments(a,contrast):
    # dY=-(Y/tau)dt+sqrt((1-Y^2)/(a*tau))dW, stationary scaled
    # beta(a,a) on [-1,1]; Z=sqrt(2a+1)*Y has variance 1.
    # E[Z_t Z_0]=exp(-|t|/tau), thus exact mean/covariance of
    # rate*(1+contrast*Z_t) match symmetric telegraph.
    assert 0<a and 0<contrast<1/math.sqrt(2*a+1)
    fourth=3*(2*a+1)/(2*a+3)
    return {'a':a,'third_cumulant':0.,'fourth_cumulant':fourth-3,
            'support_min_relative_intensity':1-contrast*math.sqrt(2*a+1),
            'support_max_relative_intensity':1+contrast*math.sqrt(2*a+1),
            'telegraph_fourth_cumulant':-2.,
            'fourth_cumulant_difference':(fourth-3)-(-2.)}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--draws',type=int,default=40000)
    p.add_argument('--seed',type=int,default=20261030)
    p.add_argument('--out',default='')
    a=p.parse_args()
    assert a.draws>2000
    rng=np.random.default_rng(a.seed)
    scenarios=[]
    for rate,contrast,T in [(1000.,.30,.01),(1000.,.30,.1),(5000.,.30,.1),(1000.,.60,.1)]:
        tau=.1
        x=event_exact_telegraph(rng,a.draws,rate,contrast,tau,T).astype(float)
        # biased moment estimators converge to true K2^F as n grows
        measured_k2=np.mean((x-x.mean())**2)-x.mean()
        theory=integrated_variance(rate,contrast,tau,T)
        mean_theory=rate*T
        scenarios.append({'rate_per_second':rate,'contrast':contrast,'tau_seconds':tau,
                          'exposure_seconds':T,'draws':a.draws,'theoretical_mean':mean_theory,
                          'empirical_mean':float(x.mean()),'theoretical_k2_factorial':theory,
                          'empirical_k2_factorial':float(measured_k2),
                          'relative_k2_error':float((measured_k2-theory)/theory)})
    dt=.005;tau=.1
    p_wrong=1-math.exp(-2*dt/tau)
    p_true=(1-math.exp(-dt/tau))/2
    rho_wrong=1-2*p_wrong
    tau_eff=-dt/math.log(rho_wrong)
    result={'status':'REPRODUCIBLE_INDEPENDENT_CALCULATION_NOT_EMPIRICAL_SERS_EVIDENCE',
            'seed':a.seed,'p_wrong_at_dt005':p_wrong,'p_correct_at_dt005':p_true,
            'wrong_telegraph_effective_tau_at_dt005':tau_eff,
            'correct_jump_hazard_per_second':1/(2*tau),'exact_theory_and_mc':scenarios,
            'strong_continuous_bounded_null':jacobi_null_moments(.2,.6),
            'interpretation':'This checks second-order moment matching and constructs an adversarial continuous null. This is NOT a controlled false-positive or power analysis, nor a calibrated SERS mechanism.'}
    out=json.dumps(result,ensure_ascii=False,indent=2)
    if a.out:
        from pathlib import Path
        path=Path(a.out);path.write_text(out+'\n',encoding='utf8')
    print(out)
if __name__=='__main__':main()
