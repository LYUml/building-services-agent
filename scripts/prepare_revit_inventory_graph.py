"""Prepare a manual-run Dynamo graph; does not open Revit or execute its API."""
import argparse
import hashlib
import json
from pathlib import Path
import uuid


def prepare(model, output):
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
            "import json\n" + source.decode("utf-8") + "\n"
            "result = inventory(DocumentManager.Instance.CurrentDBDocument, " + repr(str(model)) + ")\n"
            "result['inventory_source_sha256'] = " + repr(source_hash) + "\n"
            "with open(" + repr(str(report)) + ", 'x', encoding='utf-8') as stream:\n"
            "    json.dump(result, stream, indent=2)\n"
            "OUT = " + repr(str(report)) + "\n")
    node_id = uuid.uuid4().hex
    graph = {
        "Uuid": str(uuid.uuid4()), "IsCustomNode": False,
        "Name": "BSA read-only native pipe inventory",
        "Description": "Prepared integration; native execution not yet verified",
        "ElementResolver": {"ResolutionMap": {}},
        "Nodes": [{"ConcreteType": "PythonNodeModels.PythonNode, PythonNodeModels",
                   "Code": code, "Engine": "PythonNet3", "VariableInputPorts": True,
                   "Id": node_id, "NodeType": "PythonScriptNode", "Inputs": [],
                   "Outputs": [{"Id": uuid.uuid4().hex, "Name": "OUT",
                                "Description": "Report path", "UsingDefaultValue": False,
                                "Level": 2, "UseLevels": False, "KeepListStructure": False}],
                   "Replication": "Disabled"}],
        "Connectors": [], "Dependencies": [], "Bindings": [],
        "View": {"Dynamo": {"RunType": "Manual", "RunPeriod": "100",
                             "HasRunWithoutCrash": False},
                 "NodeViews": [{"Id": node_id, "Name": "Read native pipes",
                                "IsSetAsInput": False, "IsSetAsOutput": True,
                                "Excluded": False, "ShowGeometry": False, "X": 0, "Y": 0}],
                 "Annotations": [], "X": 0, "Y": 0, "Zoom": 1},
    }
    compile(code, "dynamo-inventory", "exec")
    output.mkdir(parents=True)
    (output / "inventory.dyn").write_text(json.dumps(graph, indent=2), encoding="utf-8")
    (output / "preparation.json").write_text(json.dumps({
        "expected_document": str(model), "source_sha256": source_hash,
        "graph_sha256": hashlib.sha256((output / "inventory.dyn").read_bytes()).hexdigest(),
        "native_executed": False, "design_accepted": False,
    }, indent=2), encoding="utf-8")
    return output / "inventory.dyn"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(prepare(args.model, args.out))
