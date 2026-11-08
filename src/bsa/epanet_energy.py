"""Independent scalar head-loss audit of EPANET results, without calling WNTR.

Original equations-based implementation. Reference conventions: EPANET 2.2
manual section 12.1 and OWA v2.2 types.h/input1.c/hydcoeffs.c; see WATER_GRAPHS.md.
These constants reproduce the engine's legacy units, not standard SI gravity.
"""
import math

M_PER_FT=.3048
M3_PER_ENGINE_FT3=.028317
REFERENCE_NU_FT2_S=1.1e-5
ENGINE_G_FT_S2=32.2
ENGINE_MINOR_COEFFICIENT=.02517


def darcy_factor(reynolds,relative_roughness):
    """Laminar, Swamee-Jain, or endpoint/slope Hermite transition factor.

    Hermite endpoints are f(2000)=64/2000 and f(4000)=Swamee-Jain(4000),
    with their analytic slopes. This expresses Dunlop's cubic independently
    of the solver's expanded polynomial and needs no solver derivatives.
    """
    if reynolds==0:return None,'stagnant'
    if reynolds<=2000:return 64/reynolds,'laminar'
    def turbulent(re):
        return .25/math.log10(relative_roughness/3.7+5.74/re**.9)**2
    if reynolds>=4000:return turbulent(reynolds),'turbulent'
    t=(reynolds-2000)/2000
    low=64/2000;high=turbulent(4000)
    u=relative_roughness/3.7+5.74/4000**.9
    low_slope=-64/2000
    high_slope=2000*.45*5.74/(math.log(10)*u*4000**1.9*math.log10(u)**3)
    f=(2*t**3-3*t**2+1)*low+(t**3-2*t**2+t)*low_slope+(-2*t**3+3*t**2)*high+(t**3-t**2)*high_slope
    return f,'transition'


def pipe_loss(pipe,flow_m3_s,relative_viscosity):
    """Signed friction+minor head in metres using documented engine conventions."""
    q=flow_m3_s/M3_PER_ENGINE_FT3;d=pipe['diameter_m']/M_PER_FT
    length=pipe['length_m']/M_PER_FT;nu=relative_viscosity*REFERENCE_NU_FT2_S
    re=4*abs(q)/(math.pi*d*nu)
    f,regime=darcy_factor(re,pipe['roughness_m']/pipe['diameter_m'])
    if re<=2000:
        # Poiseuille form stays defined at zero flow.
        friction=128*length*nu*q/(math.pi*ENGINE_G_FT_S2*d**4)
    else:
        velocity=q/(math.pi*d*d/4)
        friction=math.copysign(f*length/d*velocity**2/(2*ENGINE_G_FT_S2),q)
    minor=ENGINE_MINOR_COEFFICIENT*pipe['minor_k']*q*abs(q)/d**4
    return dict(reynolds=re,regime=regime,darcy_factor=f,
                friction_head_m=friction*M_PER_FT,minor_head_m=minor*M_PER_FT,
                model_head_loss_m=(friction+minor)*M_PER_FT)


def audit_pipe(pipe,flow_m3_s,head_from_m,head_to_m,fluid,solver):
    result=pipe_loss(pipe,flow_m3_s,fluid['relative_viscosity'])
    observed=head_from_m-head_to_m;model=result['model_head_loss_m']
    tolerance=solver['energy_absolute_tolerance_m']+solver['energy_relative_tolerance']*max(abs(model),abs(observed))
    result.update(observed_head_drop_m=observed,energy_residual_m=observed-model,
                  energy_tolerance_m=tolerance,energy_pass=abs(observed-model)<=tolerance)
    return result
