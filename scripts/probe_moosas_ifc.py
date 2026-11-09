"""Exercise pinned MOOSAS IFC loading and expose silent space loss; no simulation."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

PIN = "dbf4eb6ed955a1ba9d5052ed0e1d4a9f3411a66c"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--ifc", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    checkout, source, output = args.upstream.resolve(), args.ifc.resolve(), args.out.resolve()
    if not all(path.is_relative_to(root) for path in (checkout, source, output)) or output.exists():
        parser.error("Use repository-local inputs and a new output file")
    head = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
    changes = subprocess.check_output(["git", "-C", str(checkout), "status", "--porcelain", "--untracked-files=normal"], text=True).strip()
    if head != PIN or changes:
        parser.error("Expected exact clean pinned upstream checkout")
    before = digest(source)
    sys.path.insert(0, str(checkout))
    from MoosasPy.model.io.ifc import loadIfc, inspect_ifc
    import ifcopenshell
    original = ifcopenshell.open(str(source))
    spaces = [{"guid": x.GlobalId, "name": x.Name} for x in original.by_type("IfcSpace")]
    counts = inspect_ifc(source)
    loaded = loadIfc(source)
    unchanged = before == digest(source)
    count_preserved = len(spaces) == len(loaded.spaceList)
    report = dict(repository="https://github.com/KLEGB/MOOSAS", commit=PIN,
                  scope="Executed IFC loader/count diagnostic; no geometry or analysis acceptance",
                  source_sha256=before, source_spaces=spaces, source_counts=counts,
                  loaded_space_count=len(loaded.spaceList), loaded_face_count=len(loaded.faceList),
                  loaded_wall_count=len(loaded.wallList), reported_mode=loaded.ifcLoadMode,
                  source_unchanged=unchanged, space_count_preserved=count_preserved,
                  geometry_verified=False, simulation_executed=False, design_accepted=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps({"source_spaces": len(spaces), "loaded_spaces": len(loaded.spaceList),
                      "space_count_preserved": count_preserved, "report": str(output)}))
    return 0 if unchanged and count_preserved and spaces else 2


if __name__ == "__main__":
    raise SystemExit(main())
