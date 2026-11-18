import argparse
import html
import json
from pathlib import Path
from .engine import ProjectError, calculate, validate
from .source_refs import file_hash as digest


def dxf(p):
    import io
    import ezdxf
    doc = ezdxf.new("R2010")
    doc.units = 6  # metres, DXF $INSUNITS
    doc.layers.new("BSA_DEVICES", dxfattribs={"color": 2})
    doc.layers.new("BSA_LABELS", dxfattribs={"color": 7})
    msp = doc.modelspace()
    for d in p["devices"]:
        msp.add_circle((d["x_m"], d["y_m"]), 0.12,
                       dxfattribs={"layer": "BSA_DEVICES"})
        msp.add_text(d["id"] + " / " + d["circuit"], dxfattribs={
            "layer": "BSA_LABELS", "height": 0.12,
            "insert": (d["x_m"] + 0.2, d["y_m"])})
    stream = io.StringIO()
    doc.write(stream)
    return stream.getvalue()


def run(project, out):
    from . import workspace
    project = Path(project).resolve()
    out = Path(out).resolve()
    if not workspace.allowed(project) or not workspace.intake_output(out):
        raise ProjectError('Explicit selected project input and output workspace required')
    if project == out or out in project.parents:
        raise ProjectError("output directory must not contain the input project")
    before = digest(project)
    p = validate(json.loads(project.read_text(encoding="utf-8-sig")))
    result = calculate(p)
    if any(not d["id"].isascii() or not d["circuit"].isascii() or
           any(x in d["id"]+d["circuit"] for x in "\r\n") for d in p["devices"]):
        raise ProjectError("DXF labels currently require ASCII IDs without line breaks")
    # Never silently overwrite a previous run or unrelated files.
    out.mkdir(parents=True, exist_ok=False)
    (out/"calculations.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    (out/"devices.dxf").write_text(dxf(p),encoding="ascii")
    ds = p["devices"]
    xmin=min(d["x_m"] for d in ds)-1; ymin=min(d["y_m"] for d in ds)-1
    width=max(d["x_m"] for d in ds)-xmin+2; height=max(d["y_m"] for d in ds)-ymin+2
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{xmin} {ymin} {width} {height}">']
    for d in ds:
        svg.append(f'<circle cx="{d["x_m"]}" cy="{d["y_m"]}" r="0.12" fill="none" stroke="black" stroke-width="0.02"/>')
        svg.append(f'<text x="{d["x_m"]+0.2}" y="{d["y_m"]}" font-size="0.15">{html.escape(d["id"]+" / "+d["circuit"])}</text>')
    svg.append('</svg>')
    (out/"preview.svg").write_text("".join(svg),encoding="utf-8")
    rows="".join(f'<tr><td>{html.escape(c["id"])}</td><td>{c["design_current_a"]:.3f}</td><td>{c["voltage_drop_percent"]:.3f}</td><td>{all(c["checks"].values())}</td></tr>' for c in result["circuits"])
    sources="".join(f'<li>{html.escape(k)}: {html.escape(v)}</li>' for k,v in p["sources"].items())
    (out/"report.html").write_text('<!doctype html><meta charset="utf-8"><title>BSA conditional analysis</title><h1>'+html.escape(p["name"])+
        '</h1><p>Conditional calculation only. Design acceptance: PENDING. Geometry in metres; SVG is a schematic preview with downward Y, not a plotted CAD sheet.</p><table border="1"><tr><th>Circuit</th><th>Ib (A)</th><th>Voltage drop (%)</th><th>Calculated checks pass</th></tr>'+rows+
        '</table><h2>Unresolved checks</h2><ul>'+''.join('<li>'+html.escape(x)+'</li>' for x in result['pending'])+'</ul><h2>Input sources</h2><ul>'+sources+'</ul><img src="preview.svg" alt="Schematic device overlay">',encoding="utf-8")
    if digest(project)!=before:
        raise ProjectError("input changed during run")
    manifest=dict(input_path=str(project),input_sha256=before,input_unchanged=True,
        device_count=len(ds),dxf_circle_count=(out/"devices.dxf").read_text().count("\nCIRCLE\n"),
        outputs={f.name:digest(f) for f in out.iterdir() if f.is_file()})
    if manifest["device_count"]!=manifest["dxf_circle_count"]:
        raise ProjectError("drawing device count mismatch")
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    return result


def main():
    parser=argparse.ArgumentParser(description="Building Services Agent engineering tools")
    sub=parser.add_subparsers(dest="command",required=True)
    from .knowledge.cli import configure as configure_knowledge
    configure_knowledge(sub)
    from .changes.cli import configure as configure_changes
    configure_changes(sub)
    from . import air_terminal_review, revit_automation_reopen, revit_connectivity, revit_request
    from . import fds_temperature
    fds_temperature.add_arguments(sub.add_parser(
        'fds-temperature-probe', help='Run a pinned Windows FDS temperature case'))
    sub.add_parser('fds-temperature-verify', help='Reconcile a saved FDS probe report').add_argument('out',type=Path)
    from . import openfoam_history
    openfoam_history.add_arguments(sub.add_parser(
        'openfoam-history-review', help='Review a saved OpenFOAM steady history segment'))
    steady_verify = sub.add_parser('openfoam-history-verify', help='Verify a saved OpenFOAM steady history review')
    steady_verify.add_argument('--manifest', required=True)
    steady_verify.add_argument('--report', required=True)
    steady_verify.add_argument('--window', type=int, default=200)
    transient = sub.add_parser('openfoam-pressure-review', help='Review saved OpenFOAM physical-time pressure differences')
    transient.add_argument('--manifest', required=True)
    transient.add_argument('--output', required=True)
    transient_verify = sub.add_parser('openfoam-pressure-verify', help='Verify a saved OpenFOAM physical-time pressure report')
    transient_verify.add_argument('--manifest', required=True)
    transient_verify.add_argument('--report', required=True)
    ports=sub.add_parser('ifc-port-inventory',help='Read a saved IFC2X3 or IFC4 port inventory')
    ports.add_argument('source',type=Path)
    ports.add_argument('--baseline',type=Path)
    ports.add_argument('--position-tolerance-m',type=float)
    ports.add_argument('--max-port-shift-m',type=float)
    ports.add_argument('--alignment',type=Path)
    bcf=sub.add_parser('ifc-port-bcf',help='Export IFC port gaps and owner conflicts as BCF issues')
    bcf.add_argument('source',type=Path)
    bcf.add_argument('--out',type=Path,required=True)
    bcf.add_argument('--tolerance-m',type=float,required=True)
    bcf_verify=sub.add_parser('ifc-port-bcf-verify',help='Verify an existing IFC port coordination BCF')
    bcf_verify.add_argument('source',type=Path)
    bcf_verify.add_argument('archive',type=Path)
    bcf_verify.add_argument('--tolerance-m',type=float,required=True)
    for command in (bcf,bcf_verify):
        command.add_argument('--baseline',type=Path)
        command.add_argument('--max-port-shift-m',type=float)
        command.add_argument('--alignment',type=Path)
        command.add_argument('--require-pass', action='store_true',
                             help='Exit 2 unless the scoped IFC port review passes')
    ports.add_argument('--out',type=Path,required=True)
    revit_connectivity.add_arguments(sub.add_parser(
        'revit-inventory-check', help='Diagnose a saved Revit pipe and fitting inventory'))
    revit_request.add_arguments(sub.add_parser(
        'revit-prepare-pipe', help='Prepare a source-bound native Revit pipe request offline'))
    revit_metadata = sub.add_parser('revit-file-metadata', help='Read selected metadata from a saved RVT offline')
    revit_metadata.add_argument('source', type=Path)
    revit_metadata.add_argument('--engine-release', type=int)
    dwg_readback = sub.add_parser('dwg-readback', help='Read a saved DWG with the optional independent reader')
    dwg_readback.add_argument('source', type=Path)
    dwg_readback.add_argument('--out', type=Path, required=True)
    dwg_readback.add_argument('--reference-dxf', type=Path)
    ids_check = sub.add_parser('ids-check', help='Check saved IFC information requirements with IfcTester')
    ids_check.add_argument('ids', type=Path)
    ids_check.add_argument('ifc', type=Path)
    ids_check.add_argument('--out', type=Path, required=True)
    revit_automation_reopen.add_arguments(sub.add_parser(
        'revit-verify-automation-reopen', help='Reconcile saved Revit Automation creation and reopen evidence'))
    group=sub.add_parser('engineering-data',help='Export or verify a source-bound common data view')
    commands=group.add_subparsers(dest='data_command',required=True)
    task=commands.add_parser('context');task.add_argument('--name',required=True);task.add_argument('--scenario',required=True);task.add_argument('--out',type=Path,required=True)
    task=commands.add_parser('export');task.add_argument('source_result',type=Path);task.add_argument('--out',type=Path,required=True);task.add_argument('--include-inputs',action='store_true')
    task=commands.add_parser('verify');task.add_argument('out',type=Path)
    check=sub.add_parser('doctor',help='Read-only checks of selected pinned dependencies and host paths')
    check.add_argument('--extra',action='append',default=[])
    check.add_argument('--autocad',type=Path)
    check.add_argument('--dwg-readback',action='store_true',help='Check ACadSharp paths in the current process environment')
    check.add_argument('--mcp-config',type=Path,help='Read-only path checks of an explicit project MCP profile')
    group=sub.add_parser('drawing',help='Author or inspect general 2D drawings using the shared MCP adapters')
    commands=group.add_subparsers(dest='drawing_command',required=True)
    for action in ('run','inspect'):
        task=commands.add_parser(action)
        task.add_argument('project',type=Path)
        task.add_argument('--out',type=Path,required=True)
        if action=='run':
            task.add_argument('--autocad',type=Path,required=True)
            task.add_argument('--graphviz',type=Path)
        else:
            task.add_argument('--independent-report',type=Path,help='Write a separate DWG readback report for a verified revision')
    for name in ('autocad-source','autocad-sheet'):
        group=sub.add_parser(name,help='Source-bound AutoCAD intake or schedule writing; acceptance remains scoped')
        commands=group.add_subparsers(dest='cad_command',required=True)
        task=commands.add_parser('verify');task.add_argument('out',type=Path)
        task=commands.add_parser('run');task.add_argument('--source',type=Path,required=True)
        task.add_argument('--out',type=Path,required=True);task.add_argument('--autocad',type=Path)
        if name=='autocad-sheet':
            for flag in ('project','binding'):task.add_argument('--'+flag,type=Path,required=True)
            for flag in ('allocation-project','native-settings','original-plan'):task.add_argument('--'+flag,type=Path)
    s=sub.add_parser('project-start',help='Stage a brief and build the source interpretation handoff')
    s.add_argument('brief',type=Path);s.add_argument('--out',type=Path,required=True)
    s.add_argument('--supplement',type=Path,action='append',default=[])
    s.add_argument('--reference',type=Path,action='append',default=[])
    s=sub.add_parser('handoff',help='Execute an explicit source-bound host interpretation')
    s.add_argument('plan',type=Path);s.add_argument('interpretation',type=Path)
    s.add_argument('--target',type=Path,required=True);s.add_argument('--out',type=Path,required=True)
    for flag in ('energyplus','autocad','radiance-bin','ifcmcp-python','three-phase-python','graphviz','pdf2plot-python','honeybee-python'):
        s.add_argument('--'+flag,type=Path)
    s.add_argument('--module-provider',action='append',default=[])
    s.add_argument('--disable-module-provider',action='append',default=[])
    s.add_argument('--moosas-upstream',type=Path)
    s.add_argument('--moosas-deps',type=Path)
    s=sub.add_parser('handoff-verify',help='Reconstruct source and execution correspondence; not design acceptance')
    s.add_argument('out',type=Path)
    s=sub.add_parser('handoff-template',help='Prepare the exact blocked engineering interpretation contract')
    s.add_argument('plan',type=Path);s.add_argument('--out',type=Path,required=True)
    s=sub.add_parser('workflow-verify',help='Check saved workflow integrity without executing engines')
    s.add_argument('run',type=Path)
    s=sub.add_parser('workflow-status',help='Inspect source-bound execution blockers without rerunning')
    s.add_argument('plan',type=Path);s.add_argument('run',type=Path)
    group=sub.add_parser('delivery',help='Prepare or audit separate source-bound delivery reviews')
    commands=group.add_subparsers(dest='delivery_command',required=True)
    for action in ('template','audit'):
        task=commands.add_parser(action)
        task.add_argument('plan',type=Path);task.add_argument('run',type=Path)
        task.add_argument('--out',type=Path,required=True)
        if action=='audit':task.add_argument('--review',type=Path,required=True)
    archive=commands.add_parser('verify-archive',help='Verify ZIP members against a SHA-256 manifest')
    archive.add_argument('archive',type=Path)
    archive.add_argument('manifest',type=Path)
    air_terminal_review.add_arguments(commands.add_parser(
        'verify-terminal-connections', help='Check saved terminal connections from a verified native workflow'))
    hvac_package = commands.add_parser('inspect-hvac-package', help='Inspect a saved HVAC project package')
    hvac_package.add_argument('configuration', type=Path)
    hvac_package.add_argument('package', type=Path)
    contacts = commands.add_parser('verify-three-phase-contacts', help='Check bus contacts in a saved schematic DXF')
    for argument in ('project', 'study', 'drawing'):
        contacts.add_argument(argument, type=Path)
    recovery = commands.add_parser('verify-recovery', help='Verify a saved fan or pump recovery controller receipt')
    recovery.add_argument('directory', type=Path)
    for command in ("validate","run"):
        s=sub.add_parser(command);s.add_argument("project",type=Path)
        if command=="run": s.add_argument("--out",type=Path,required=True)
    s=sub.add_parser("workflow",help="Execute a source-linked plan and retain dependency diagnosis")
    s.add_argument("plan",type=Path)
    s.add_argument("--out",type=Path,required=True)
    s.add_argument("--review",type=Path,help="Create a pending delivery review outside the run directory")
    for flag in ("energyplus","autocad","radiance-bin","ifcmcp-python","three-phase-python","graphviz","pdf2plot-python","honeybee-python","requirements-result","fds-release"):
        s.add_argument("--"+flag,type=Path)
    s.add_argument('--module-provider',action='append',default=[])
    s.add_argument('--disable-module-provider',action='append',default=[])
    s.add_argument('--moosas-upstream',type=Path)
    s.add_argument('--moosas-deps',type=Path)
    a=parser.parse_args()
    try:
        if a.command=='delivery' and a.delivery_command=='verify-archive':
            from .delivery_archive import verify_archive
            print(json.dumps(verify_archive(a.archive,a.manifest),indent=2));return 0
        if a.command=='delivery' and a.delivery_command=='verify-terminal-connections':
            args=vars(a).copy()
            del args['command'], args['delivery_command']
            print(json.dumps(air_terminal_review.review(**args),indent=2));return 0
        if a.command=='delivery' and a.delivery_command=='verify-three-phase-contacts':
            from .three_phase_drawing import verify_contacts
            print(json.dumps(verify_contacts(a.project, a.study, a.drawing), indent=2));return 0
        if a.command=='delivery' and a.delivery_command=='inspect-hvac-package':
            from .hvac_package_access import inspect
            result = inspect(a.configuration, a.package)
            print(json.dumps(result, indent=2))
            return 2 if result['status'] == 'incomplete' else 0
        if a.command=='delivery' and a.delivery_command=='verify-recovery':
            from .recovery_controller import verify
            print(json.dumps(verify(a.directory), indent=2));return 0
        if a.command=='ifc-port-bcf':
            from .ifc_port_bcf import run as export_bcf
            result=export_bcf(a.source,a.out,a.tolerance_m,baseline=a.baseline,
                              max_port_shift_m=a.max_port_shift_m,alignment=a.alignment)
            print(json.dumps(result, indent=2))
            return 2 if a.require_pass and result['ifc_review_status'] != 'pass' else 0
        if a.command=='ifc-port-bcf-verify':
            from .ifc_port_bcf import verify_export
            result=verify_export(a.source,a.archive,a.tolerance_m,baseline=a.baseline,
                                 max_port_shift_m=a.max_port_shift_m,alignment=a.alignment)
            print(json.dumps(result, indent=2))
            return 2 if a.require_pass and result['ifc_review_status'] != 'pass' else 0
        if a.command=='ifc-port-inventory':
            from .ifc_port_inventory import run as inventory_ports
            result=inventory_ports(a.source,a.out,baseline=a.baseline,position_tolerance_m=a.position_tolerance_m,
                                   max_port_shift_m=a.max_port_shift_m,alignment=a.alignment)
            print(json.dumps(result,indent=2));return 0
        if a.command=='fds-temperature-probe':
            print(json.dumps(fds_temperature.run(a.release,a.source,a.out),indent=2));return 0
        if a.command=='fds-temperature-verify':
            print(json.dumps(fds_temperature.verify(a.out),indent=2));return 0
        if a.command=='openfoam-history-review':
            result = openfoam_history.review_project(a.manifest, a.output, window=a.window)
            print(json.dumps(result, indent=2));return 0 if result['numerical_window_pass'] else 2
        if a.command=='openfoam-history-verify':
            print(json.dumps(openfoam_history.verify_project(a.manifest, a.report, window=a.window), indent=2));return 0
        if a.command=='openfoam-pressure-review':
            from .openfoam_transient import review_pressure_project
            print(json.dumps(review_pressure_project(a.manifest, a.output), indent=2));return 0
        if a.command=='openfoam-pressure-verify':
            from .openfoam_transient import verify_pressure_project
            print(json.dumps(verify_pressure_project(a.manifest, a.report), indent=2));return 0
        if a.command=='revit-prepare-pipe':
            from .workspace import project_root
            result=revit_request.prepare(a.inventory,a.model,a.basis,a.out,scope=project_root())
            print(json.dumps(result,indent=2));return 0
        if a.command=='revit-file-metadata':
            from .revit_file_metadata import inspect
            print(json.dumps(inspect(a.source, a.engine_release),indent=2));return 0
        if a.command=='dwg-readback':
            from .dwg_readback import run as read_dwg
            result = read_dwg(a.source, a.out, a.reference_dxf)
            print(json.dumps(result, indent=2));return 2 if result.get('correspondence_pass') is False else 0
        if a.command == 'ids-check':
            from .ids_check import run as check_ids
            result = check_ids(a.ids, a.ifc, a.out)
            print(json.dumps(result, indent=2))
            return 0 if result['calculated_checks_pass'] else 2
        if a.command=='revit-inventory-check':
            result=revit_connectivity.run(a.inventory,a.model,a.out,a.tolerance_m,
                                          expected_connections=a.expected_connections,
                                          automation_receipt=a.automation_receipt)
            print(json.dumps(result,indent=2));return 2
        if a.command=='revit-verify-automation-reopen':
            result=revit_automation_reopen.verify(a.write_stage,a.creation,a.authored,a.inventory,
                                                  a.reopen_preparation,a.tolerance_m)
            print(json.dumps(result,indent=2));return 0
        if a.command=='changes':
            from .changes.cli import dispatch
            print(json.dumps(dispatch(a),indent=2));return 0
        if a.command=='knowledge':
            from .knowledge.cli import dispatch
            print(json.dumps(dispatch(a),indent=2));return 0
        if a.command=='engineering-data':
            if a.data_command=='context':
                from .engineering_data.context import create
                print(json.dumps(create(a.name,a.scenario,a.out),indent=2));return 0
            from .engineering_data.module_bridge import export,verify
            result=export(a.source_result,a.out,include_inputs=a.include_inputs) if a.data_command=='export' else verify(a.out)
            print(json.dumps(result,indent=2));return 0
        if a.command=='doctor':
            from .doctor import check
            result=check(extras=a.extra,autocad=a.autocad,mcp_config=a.mcp_config,dwg_readback=a.dwg_readback)
            print(json.dumps(result,indent=2));return 0 if result['status']=='direct_requirements_ready' else 2
        if a.command=='drawing':
            from . import drawing_access
            # Use exactly the MCP boundary and its schema dispatch; no second engine.
            try:
                if a.drawing_command=='run':
                    result=drawing_access.run(a.project,a.out,autocad=a.autocad,graphviz=a.graphviz)
                elif a.independent_report is not None:
                    result=drawing_access.inspect_revision_readback(a.project,a.out,a.independent_report)
                else:
                    result=drawing_access.inspect(a.project,a.out)
            except (KeyError,TypeError) as error:
                raise ProjectError(f'Drawing {a.drawing_command} failed: {error}') from error
            print(json.dumps(result,indent=2))
            return 2 if result.get('independent_readback', {}).get('correspondence_pass') is False else 0
        if a.command in ('autocad-source','autocad-sheet'):
            # Paths and runtime are explicit host arguments; adapters retain all gates.
            if a.command=='autocad-source':
                from . import autocad_source as adapter
            else:
                from . import autocad_schedule as adapter
            if a.cad_command=='verify':
                print(json.dumps(adapter.verify(a.out),indent=2));return 0
            if a.command=='autocad-source':
                result=adapter.run(a.source,a.out,autocad=a.autocad)
                expected='inspected'
            else:
                result=adapter.run(a.source,a.project,a.binding,a.out,allocation_project=a.allocation_project,
                    native_settings=a.native_settings,autocad=a.autocad,original_plan=a.original_plan)
                expected='written'
            keys=('status','inputs_unchanged','native_reopen_pass','plot_visual_review','design_accepted','error')
            print(json.dumps({k:result[k] for k in keys if k in result},indent=2))
            return 0 if result['status']==expected else 2
        if a.command=='project-start':
            from .project_start import start
            result=start(a.brief,a.out,supplements=a.supplement,references=a.reference)
            print(json.dumps({key:result[key] for key in ('status','effective_plan','interpretation_template_ready','stage_errors','design_accepted')},indent=2))
            return 2
        elif a.command=='handoff-template':
            from .engineering_handoff import template
            print(json.dumps(template(a.plan,a.out),indent=2));return 2
        elif a.command=='handoff':
            from .engineering_handoff import run as handoff
            from .workflow_modules import parse_provider_options
            names=('energyplus','autocad','radiance_bin','ifcmcp_python','three_phase_python','graphviz','pdf2plot_python','honeybee_python')
            options={key:getattr(a,key) for key in names if getattr(a,key) is not None}
            options.update(module_providers=parse_provider_options(a.module_provider),disabled_module_providers=a.disable_module_provider)
            options['module_runtime']={key:value for key,value in dict(upstream=a.moosas_upstream,deps=a.moosas_deps).items() if value is not None}
            result=handoff(a.plan,a.interpretation,a.target,a.out,execute_options=options)
            print(json.dumps({key:result[key] for key in ('status','stages','stage_errors','design_accepted')},indent=2))
            return 2
        elif a.command=='handoff-verify':
            from .engineering_handoff import verify
            print(json.dumps(verify(a.out),indent=2));return 0
        elif a.command=='workflow-verify':
            from .workflow import verify
            result=verify(a.run)
            print(json.dumps(result,ensure_ascii=False,indent=2))
            return 0 if result['integrity_pass'] else 2
        elif a.command=='workflow-status':
            from .workflow_status import diagnose
            result=diagnose(a.plan,a.run)
            print(json.dumps(result,ensure_ascii=False,indent=2))
            return 0 if result['execution_pass'] else 2
        elif a.command=='delivery':
            from . import delivery
            if a.delivery_command=='template':
                result=delivery.template(a.plan,a.run,a.out)
                print(json.dumps(dict(review=str(a.out.resolve()),requirement_count=len(result['requirements']),
                    status='needs_review',design_accepted=False),indent=2))
                return 0
            result=delivery.run(a.plan,a.run,a.review,a.out)
            print(json.dumps(dict(output=str(a.out.resolve()),report=str((a.out/'report.html').resolve()),
                **{key:result[key] for key in ('status','review_checks_pass','design_accepted')}),indent=2))
            return 0 if result['review_checks_pass'] else 2
        elif a.command=="workflow":
            from .workflow import execute
            from .workflow_status import diagnose
            from .workflow_modules import parse_provider_options
            providers=parse_provider_options(a.module_provider)
            if a.review is not None:
                review=a.review.resolve()
                from . import workspace
                if not workspace.intake_output(review):raise ProjectError('Explicit selected delivery review output workspace required')
                if review.exists() or review==a.plan.resolve() or review.is_relative_to(a.out.resolve()):
                    raise ProjectError("review must be a new file outside the plan/run artifacts")
            execute(a.plan,a.out,a.energyplus,a.autocad,a.radiance_bin,a.ifcmcp_python,a.three_phase_python,a.graphviz,a.pdf2plot_python,a.honeybee_python,requirements_result=a.requirements_result,fds_release=a.fds_release,
                module_providers=providers,disabled_module_providers=a.disable_module_provider,
                module_runtime={key:value for key,value in dict(upstream=a.moosas_upstream,deps=a.moosas_deps).items() if value is not None})
            diagnosis=diagnose(a.plan,a.out)
            # Separate from immutable task artifacts: diagnosis binds workflow.json.
            with (a.out/"diagnosis.json").open("x",encoding="utf-8") as stream:
                json.dump(diagnosis,stream,ensure_ascii=False,indent=2)
            if a.review is not None:
                from .delivery import template
                template(a.plan,a.out,a.review)
            print(json.dumps({"output":str(a.out.resolve()),
                "report":str((a.out/"index.html").resolve()),
                "diagnosis":str((a.out/"diagnosis.json").resolve()),
                "review":str(a.review.resolve()) if a.review is not None else None,
                "execution_pass":diagnosis["execution_pass"],"design_accepted":False},indent=2))
            return 0 if diagnosis["execution_pass"] else 2
        elif a.command=="validate":
            validate(json.loads(a.project.read_text(encoding="utf-8-sig")))
            print("Valid electrical project; engineering acceptance not assessed.")
        else:
            result=run(a.project,a.out)
            print(json.dumps({"output":str(a.out),"calculated_checks_pass":result["calculated_checks_pass"],"design_accepted":False}))
            if not result["calculated_checks_pass"]: return 2
    except ModuleNotFoundError as e:
        from .cli_errors import missing_dependency
        parser.exit(2,missing_dependency(e)['message']+'\n')
    except (KeyError,TypeError) as e:
        if a.command in ('openfoam-history-review','openfoam-history-verify'):
            parser.exit(2,'Invalid OpenFOAM history evidence structure: '+str(e)+'\n')
        if a.command=='revit-verify-automation-reopen':
            parser.exit(2,'Invalid saved Revit evidence structure: '+str(e)+'\n')
        if a.command not in ('workflow-verify','workflow-status','delivery'):raise
        parser.exit(2,'Invalid saved workflow/review structure: '+str(e)+'\n')
    except (ProjectError, OSError, ValueError) as e:
        parser.exit(2,str(e)+"\n")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
