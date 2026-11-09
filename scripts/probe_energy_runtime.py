"""Probe native energy dependencies in child processes; never simulate or change policy."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def probe(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True,
                                errors="replace", timeout=30)
        return dict(command=command, returncode=result.returncode,
                    stdout=result.stdout, stderr=result.stderr,
                    launch_pass=result.returncode == 0)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return dict(command=command, returncode=None, launch_pass=False,
                    error=str(exc))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--energyplus", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.out.resolve()
    if not output.is_relative_to(root) or output.exists():
        parser.error("Choose a new output file inside this repository")
    executable = args.energyplus.resolve(strict=True)
    results = {
        "scope": "Runtime startup only; no model, simulation or engineering acceptance",
        "python": sys.executable,
        "energyplus_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
        "energyplus": probe([str(executable), "--version"]),
        "openstudio": probe([sys.executable, "-c",
            "import openstudio; print(openstudio.openStudioVersion()); print(openstudio.energyPlusVersion())"]),
        "design_accepted": False,
    }
    results["startup_pass"] = all(results[name]["launch_pass"] for name in ("energyplus", "openstudio"))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(results, stream, indent=2)
    print(json.dumps({"startup_pass": results["startup_pass"], "report": str(output)}))
    return 0 if results["startup_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
