"""Package the local Revit Automation inventory build for offline review."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


def inventory_activity(engine, bundle_id):
    if not re.fullmatch(r'Autodesk\.Revit\+2027(?:_[A-Za-z0-9]+)?', engine):
        raise ValueError('Select an explicit Revit 2027 engine from the authenticated APS catalogue')
    match = re.fullmatch(r'[A-Za-z0-9_]+\.([A-Za-z0-9_]+)\+[A-Za-z0-9_]+', bundle_id)
    if not match:
        raise ValueError('Expected a qualified APS app bundle ID as owner.bundle+alias')
    name = match.group(1)
    command = (r'$(engine.path)\revitcoreconsole.exe /i "$(args[model].path)" '
               f'/al "$(appbundles[{name}].path)"')
    return {
        'id': 'BsaRevitInventory',
        'engine': engine,
        'appbundles': [bundle_id],
        'commandLine': [command],
        'parameters': {
            name: {'localName': filename, 'verb': verb, 'required': True}
            for name, filename, verb in (
                ('model', 'input.rvt', 'get'),
                ('request', 'inventory-request.json', 'get'),
                ('inventory', 'inventory.json', 'put'),
            )
        },
    }


def inventory_request(model, runs):
    model = Path(model).resolve()
    if not model.is_relative_to(runs) or model.suffix.lower() != '.rvt' or not model.is_file():
        raise ValueError('Select a local RVT test fixture under repository runs')
    with model.open('rb') as stream:
        sha256 = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'SavedRvtSha256': sha256}


def prepare(assembly, output, *, engine=None, bundle_id=None, model=None):
    if (engine is None) != (bundle_id is None):
        raise ValueError('Supply engine and qualified bundle ID together to stage an Activity')
    activity = inventory_activity(engine, bundle_id) if engine is not None else None
    runs = Path(__file__).resolve().parents[1] / 'runs'
    assembly, output = (Path(path).resolve() for path in (assembly, output))
    if not assembly.is_relative_to(runs) or assembly.name != 'Bsa.Revit.Automation.dll':
        raise ValueError('Select the Automation DLL from a repository runs build')
    if not output.is_relative_to(runs) or output == runs or output.exists():
        raise ValueError('Select a fresh output directory under repository runs')
    request = inventory_request(model, runs) if model is not None else None

    prefix = 'Bsa.Revit.Automation.bundle'
    package = b'''<ApplicationPackage Name="Bsa.Revit.Automation" AppVersion="0.1.0">
  <CompanyDetails Name="Building Services Agent" />
  <Components>
    <RuntimeRequirements SeriesMin="R2027" SeriesMax="R2027" Platform="Revit" OS="Win64" />
    <ComponentEntry LoadOnRevitStartup="True" LoadOnCommandInvocation="False"
                    ModuleName="./Contents/Bsa.Revit.Automation.addin" />
  </Components>
</ApplicationPackage>
'''
    addin = b'''<RevitAddIns>
  <AddIn Type="DBApplication">
    <Name>BSA Revit Inventory</Name>
    <Assembly>.\\Bsa.Revit.Automation.dll</Assembly>
    <FullClassName>Bsa.Revit.AutomationInventory</FullClassName>
    <AddInId>dc18527a-ebbc-4fcb-9cb0-6df138047769</AddInId>
    <VendorId>BSA</VendorId>
  </AddIn>
</RevitAddIns>
'''
    payload = {
        f'{prefix}/PackageContents.xml': package,
        f'{prefix}/Contents/Bsa.Revit.Automation.addin': addin,
        f'{prefix}/Contents/{assembly.name}': assembly.read_bytes(),
    }
    output.mkdir(parents=True)
    archive = output / 'Bsa.Revit.Automation.zip'
    with ZipFile(archive, 'x', compression=ZIP_DEFLATED) as bundle:
        for name, content in payload.items():
            member = ZipInfo(name)
            member.create_system = 3
            member.external_attr = 0o100644 << 16
            bundle.writestr(member, content, compress_type=ZIP_DEFLATED)
    with ZipFile(archive) as bundle:
        if bundle.namelist() != list(payload) or any(bundle.read(name) != data for name, data in payload.items()):
            raise ValueError('AppBundle differs from the selected files')
    receipt = {
        'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
        'assembly_sha256': hashlib.sha256(payload[f'{prefix}/Contents/{assembly.name}']).hexdigest(),
        'uploaded': False,
        'native_executed': False,
    }
    if activity is not None:
        activity_bytes = json.dumps(activity, indent=2).encode('utf-8')
        (output / 'activity.json').write_bytes(activity_bytes)
        receipt['activity_sha256'] = hashlib.sha256(activity_bytes).hexdigest()
    if request is not None:
        if inventory_request(model, runs) != request:
            raise ValueError('RVT changed during preparation')
        request_bytes = json.dumps(request, indent=2).encode('utf-8')
        (output / 'inventory-request.json').write_bytes(request_bytes)
        receipt['request_sha256'] = hashlib.sha256(request_bytes).hexdigest()
        receipt['saved_rvt_sha256'] = request['SavedRvtSha256']
    (output / 'preparation.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    return archive


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assembly', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--engine')
    parser.add_argument('--bundle-id')
    parser.add_argument('--model', help='Local RVT fixture to hash for the inventory request')
    args = parser.parse_args()
    print(prepare(args.assembly, args.out, engine=args.engine, bundle_id=args.bundle_id, model=args.model))
