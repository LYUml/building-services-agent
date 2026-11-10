"""Identical independent appliance demand, using an explicit binomial model."""
import math


def identical(*,count,operating_probability,fixture_flow_L_s,exceedance_probability,basis):
    if type(count) is not int or not 1<=count<=10**9:raise ValueError('Integer appliance count in1..1e9 required')
    for name,v in [('operating probability',operating_probability),('exceedance probability',exceedance_probability)]:
        if type(v) not in (int,float) or not math.isfinite(v) or not 0<v<1:raise ValueError('Explicit '+name+' in(0,1) required')
    if type(fixture_flow_L_s) not in (int,float) or not math.isfinite(fixture_flow_L_s) or fixture_flow_L_s<=0:
        raise ValueError('Positive finite single-appliance flow in L/s required')
    if not isinstance(basis,str) or not basis.strip():raise ValueError('Explicit model/source/applicability basis required')
    import scipy
    from scipy.stats import binom
    if scipy.__version__!='1.18.1':raise ValueError('Pinned SciPy1.18.1 required')
    # isf avoids rounding 1-risk to1 for very small allowed exceedance.
    value=float(binom.isf(exceedance_probability,count,operating_probability))
    if not math.isfinite(value):raise ValueError('Binomial inverse outside numeric range')
    n=int(value)
    # Confirm the discrete minimal provision using survival tails, not ppf alone.
    while n<count and binom.sf(n,count,operating_probability)>exceedance_probability:n+=1
    while n>0 and binom.sf(n-1,count,operating_probability)<=exceedance_probability:n-=1
    tail=float(binom.sf(n,count,operating_probability));previous=float(binom.sf(n-1,count,operating_probability)) if n else None
    flow=n*fixture_flow_L_s
    if not 0<=n<=count or not math.isfinite(flow) or not math.isfinite(tail) or tail>exceedance_probability or (previous is not None and previous<=exceedance_probability):
        raise ValueError('Discrete binomial provision checks failed')
    return dict(count=count,operating_probability=operating_probability,fixture_flow_L_s=fixture_flow_L_s,
        exceedance_probability=exceedance_probability,simultaneous_appliances=n,design_flow_L_s=flow,
        actual_exceedance_probability=tail,previous_provision_exceedance_probability=previous,
        scipy_version=scipy.__version__,basis=basis,model_checks_pass=True,design_accepted=False,
        scope='Identical independent Bernoulli appliances with equal fixed operating flow; not mixed loading/discharge units, pipe sizing or code acceptance')
