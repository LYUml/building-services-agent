"""Prepare a manual-run Dynamo graph; does not open Revit or execute its API."""
import argparse
import hashlib
import json
from pathlib import Path
import uuid


def prepare(model, output, adapter=None):
    root = Path(__file__).resolve().parents[1]
    model, output = model.resolve(), output.resolve()
    if not model.is_relative_to(root) or model.suffix.lower() != ".rvt":
        raise ValueError("Expected a test RVT path within this repository")
    if not output.is_relative_to(root) or output.exists():
        raise ValueError("Choose a new run directory inside this repository")
    source = (root / "scripts/revit_inventory.py").read_bytes()
    source_hash = hashlib.sha256(source).hexdigest()
    report = output / "inventory.json"
    code = ("import clr\nclr.AddReference('RevitAPI')\n"
            "clr.AddReference('RevitServices')\n"
            "from RevitServices.Persistence import DocumentManager\n"
            "import json, hashlib\n" + source.decode("utf-8") + "\n"
            "model_path = " + repr(str(model)) + "\n"
            "def file_hash(path):\n"
            "    digest = hashlib.sha256()\n"
            "    with open(path, 'rb') as stream:\n"
            "        for block in iter(lambda: stream.read(1048576), b''):\n"
            "            digest.update(block)\n"
            "    return digest.hexdigest()\n"
            "before = file_hash(model_path)\n"
            "result = inventory(DocumentManager.Instance.CurrentDBDocument, " + repr(str(model)) + ")\n"
            "if file_hash(model_path) != before or DocumentManager.Instance.CurrentDBDocument.IsModified:\n"
            "    raise ValueError('Model changed during inventory')\n"
            "result['saved_rvt_sha256'] = before\n"
            "result['inventory_source_sha256'] = " + repr(source_hash) + "\n"
            "with open(" + repr(str(report)) + ", 'x', encoding='utf-8') as stream:\n"
            "    json.dump(result, stream, indent=2)\n"
            "OUT = " + repr(str(report)) + "\n")
    request = None
    if adapter is not None:
        adapter = adapter.resolve(strict=True)
        if not adapter.is_relative_to(root) or adapter.suffix.lower() != '.dll':
            raise ValueError('Expected a repository-local compiled adapter DLL')
        source_hash = hashlib.sha256(adapter.read_bytes()).hexdigest()
        # A distinct captured path also exposes assembly identity reuse in a running host.
        captured_adapter = output / 'Bsa.Revit.dll'
        request = dict(DocumentPath=str(model), ReportPath=str(report))
        request_text = json.dumps(request, indent=2)
        request_hash = hashlib.sha256(request_text.encode('utf-8')).hexdigest()
        code = (
            'import clr, hashlib, os\n'
            'def file_hash(path):\n'
            "    with open(path, 'rb') as stream:\n"
            '        return hashlib.sha256(stream.read()).hexdigest()\n'
            'adapter_path = ' + repr(str(captured_adapter)) + '\n'
            'request_path = ' + repr(str(output / 'request.json')) + '\n'
            'if file_hash(adapter_path) != ' + repr(source_hash) + ':\n'
            "    raise ValueError('Captured adapter changed')\n"
            'if file_hash(request_path) != ' + repr(request_hash) + ':\n'
            "    raise ValueError('Captured request changed')\n"
            "clr.AddReference('RevitAPI')\nclr.AddReference('RevitAPIUI')\n"
            "clr.AddReference('RevitServices')\n"
            'assembly = clr.AddReference(adapter_path)\n'
            'if os.path.normcase(os.path.abspath(str(assembly.Location))) != os.path.normcase(adapter_path):\n'
            "    raise ValueError('Host reused a different loaded adapter; do not run stale code')\n"
            'from RevitServices.Persistence import DocumentManager\n'
            'from Bsa.Revit import InventoryCommand\n'
            'InventoryCommand.Run(DocumentManager.Instance.CurrentUIApplication, request_path)\n'
            'OUT = ' + repr(str(report)) + '\n')
    node_id = uuid.uuid4().hex
    graph = {
        "Uuid": str(uuid.uuid4()), "IsCustomNode": False,
        "Name": "BSA read-only native pipe inventory",
        "Description": "Prepared integration; native execution not yet verified",
        "ElementResolver": {"ResolutionMap": {}},
        "Inputs": [], "Outputs": [], "NodeLibraryDependencies": [],
        "ExtensionWorkspaceData": [],
        "Nodes": [{"ConcreteType": "PythonNodeModels.PythonNode, PythonNodeModels",
                   "Code": code, "Engine": "PythonNet3", "VariableInputPorts": True,
                   "Id": node_id, "NodeType": "PythonScriptNode",
                   "Inputs": [{"Id": uuid.uuid4().hex, "Name": "IN[0]",
                               "Description": "Unused input", "UsingDefaultValue": False,
                               "Level": 2, "UseLevels": False, "KeepListStructure": False}],
                   "Outputs": [{"Id": uuid.uuid4().hex, "Name": "OUT",
                                "Description": "Report path", "UsingDefaultValue": False,
                                "Level": 2, "UseLevels": False, "KeepListStructure": False}],
                   "Replication": "Disabled"}],
        "Connectors": [], "Dependencies": [], "Bindings": [],
        "View": {"Dynamo": {"ScaleFactor": 1.0, "Version": "4.2.1.5887", "RunType": "Manual", "RunPeriod": "100",
                             "HasRunWithoutCrash": False},
                 "NodeViews": [{"Id": node_id, "Name": "Read native pipes",
                                "IsSetAsInput": False, "IsSetAsOutput": True,
                                "Excluded": False, "ShowGeometry": False, "X": 0, "Y": 0}],
                 "Annotations": [], "X": 0, "Y": 0, "Zoom": 1},
    }
    compile(code, "dynamo-inventory", "exec")
    output.mkdir(parents=True)
    if adapter is not None:
        captured = adapter.read_bytes()
        if hashlib.sha256(captured).hexdigest() != source_hash:
            raise ValueError('Adapter changed during graph preparation')
        (output / 'Bsa.Revit.dll').write_bytes(captured)
        (output / 'request.json').write_text(request_text, encoding='utf-8')
    (output / "inventory.dyn").write_text(json.dumps(graph, indent=2), encoding="utf-8")
    (output / "preparation.json").write_text(json.dumps({
        "expected_document": str(model), "source_sha256": source_hash,
        "graph_sha256": hashlib.sha256((output / "inventory.dyn").read_bytes()).hexdigest(),
        "native_executed": False, "design_accepted": False,
        "implementation": "compiled-csharp" if adapter is not None else "legacy-python",
    }, indent=2), encoding="utf-8")
    return output / "inventory.dyn"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--adapter", type=Path, help="Capture the current compiled C# adapter for manual read-only invocation")
    args = parser.parse_args()
    print(prepare(args.model, args.out, args.adapter))
