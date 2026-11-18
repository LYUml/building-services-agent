"""Package the local Revit Automation build for offline review."""
import argparse
import hashlib
from http.client import HTTPSConnection
import json
import os
from pathlib import Path
import re
from urllib.parse import quote
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


def automation_activity(engine, bundle_id, operation):
    if not re.fullmatch(r'Autodesk\.Revit\+2027(?:_[A-Za-z0-9]+)?', engine):
        raise ValueError('Select an explicit Revit 2027 engine from the authenticated APS catalogue')
    match = re.fullmatch(r'[A-Za-z0-9_]+\.([A-Za-z0-9_]+)\+[A-Za-z0-9_]+', bundle_id)
    if not match:
        raise ValueError('Expected a qualified APS app bundle ID as owner.bundle+alias')
    name = match.group(1)
    command = (r'$(engine.path)\revitcoreconsole.exe /i "$(args[model].path)" '
               f'/al "$(appbundles[{name}].path)"')
    writing = operation == 'create-pipe'
    transfers = (
        ('request', 'pipe-request.json', 'get'),
        ('authored', 'authored.rvt', 'put'),
        ('creation', 'creation.json', 'put'),
    ) if writing else (
        ('request', 'inventory-request.json', 'get'),
        ('inventory', 'inventory.json', 'put'),
    )
    return {
        'id': 'BsaRevitCreatePipe' if writing else 'BsaRevitInventory',
        'engine': engine,
        'appbundles': [bundle_id],
        'commandLine': [command],
        'parameters': {
            name: {'localName': filename, 'verb': verb, 'required': True}
            for name, filename, verb in (('model', 'input.rvt', 'get'), *transfers)
        },
    }


def inventory_request(model, runs):
    model = Path(model).resolve()
    if not model.is_relative_to(runs) or model.suffix.lower() != '.rvt' or not model.is_file():
        raise ValueError('Select a local RVT test fixture under repository runs')
    with model.open('rb') as stream:
        sha256 = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'SavedRvtSha256': sha256}


def confirm_engine(engine, access_token):
    connection = HTTPSConnection('developer.api.autodesk.com', timeout=15)
    try:
        connection.request('GET', '/da/us-east/v3/engines/' + quote(engine, safe=''),
                           headers={'Authorization': 'Bearer ' + access_token, 'Accept': 'application/json'})
        response = connection.getresponse()
        if response.status != 200:
            raise ValueError(f'APS engine lookup returned HTTP {response.status}')
        data = json.loads(response.read(65536))
    finally:
        connection.close()
    if (not isinstance(data, dict) or data.get('id') != engine
            or not isinstance(data.get('productVersion'), str) or type(data.get('version')) is not int):
        raise ValueError('APS engine response did not identify the selected engine and version')
    return {key: data[key] for key in ('id', 'productVersion', 'version')}


def prepare(assembly, output, *, engine=None, bundle_id=None, model=None,
            operation='inventory', pipe_request=None, check_engine=False):
    if operation not in ('inventory', 'create-pipe'):
        raise ValueError('Unsupported Automation operation')
    writing = operation == 'create-pipe'
    if (pipe_request is not None and (not writing or model is None)
            or writing and model is not None and pipe_request is None):
        raise ValueError('Supply the test model and its prepared pipe request together for creation')
    if (engine is None) != (bundle_id is None):
        raise ValueError('Supply engine and qualified bundle ID together to stage an Activity')
    activity = automation_activity(engine, bundle_id, operation) if engine is not None else None
    runs = Path(__file__).resolve().parents[1] / 'runs'
    assembly, output = (Path(path).resolve() for path in (assembly, output))
    if not assembly.is_relative_to(runs) or assembly.name != 'Bsa.Revit.Automation.dll':
        raise ValueError('Select the Automation DLL from a repository runs build')
    if not output.is_relative_to(runs) or output == runs or output.exists():
        raise ValueError('Select a fresh output directory under repository runs')
    request = inventory_request(model, runs) if model is not None else None
    if pipe_request is not None:
        pipe_request = Path(pipe_request).resolve()
        if not pipe_request.is_relative_to(runs) or pipe_request.suffix.lower() != '.json':
            raise ValueError('Select a prepared pipe request under repository runs')
        request_bytes = pipe_request.read_bytes()
        declared = json.loads(request_bytes)
        if not isinstance(declared, dict) or declared.get('SavedRvtSha256') != request['SavedRvtSha256']:
            raise ValueError('Pipe request does not match the selected saved RVT')
    elif request is not None:
        request_bytes = json.dumps(request, indent=2).encode('utf-8')
    confirmed = None
    if check_engine:
        token = os.environ.get('APS_ACCESS_TOKEN')
        if activity is None or not token:
            raise ValueError('Engine confirmation requires Activity arguments and APS_ACCESS_TOKEN in the environment')
        confirmed = confirm_engine(engine, token)

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
    if writing:
        addin = (addin.replace(b'BSA Revit Inventory', b'BSA Revit Create Pipe')
                 .replace(b'Bsa.Revit.AutomationInventory', b'Bsa.Revit.AutomationCreatePipe')
                 .replace(b'dc18527a-ebbc-4fcb-9cb0-6df138047769', b'dd8dab45-f930-46c6-9679-32b5df58b77b'))
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
        'operation': operation,
        'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
        'assembly_sha256': hashlib.sha256(payload[f'{prefix}/Contents/{assembly.name}']).hexdigest(),
        'uploaded': False,
        'native_executed': False,
    }
    if activity is not None:
        activity_bytes = json.dumps(activity, indent=2).encode('utf-8')
        (output / 'activity.json').write_bytes(activity_bytes)
        receipt['activity_sha256'] = hashlib.sha256(activity_bytes).hexdigest()
    if confirmed is not None:
        receipt['confirmed_engine'] = confirmed
    if request is not None:
        if inventory_request(model, runs) != request:
            raise ValueError('RVT changed during preparation')
        if pipe_request is not None and pipe_request.read_bytes() != request_bytes:
            raise ValueError('Pipe request changed during preparation')
        (output / ('pipe-request.json' if writing else 'inventory-request.json')).write_bytes(request_bytes)
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
    parser.add_argument('--operation', choices=('inventory', 'create-pipe'), default='inventory')
    parser.add_argument('--model', help='Local RVT fixture to hash for the inventory request')
    parser.add_argument('--pipe-request', help='Prepared pipe request for the selected RVT fixture')
    parser.add_argument('--check-engine', action='store_true', help='Confirm engine availability with a read-only APS call')
    args = parser.parse_args()
    try:
        print(prepare(args.assembly, args.out, engine=args.engine, bundle_id=args.bundle_id, model=args.model,
                      operation=args.operation, pipe_request=args.pipe_request, check_engine=args.check_engine))
    except (OSError, ValueError) as error:
        parser.exit(2, f'{error}\n')
