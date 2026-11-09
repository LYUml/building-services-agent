"""Exercise pinned MOOSAS project generation and CONTAM on a synthetic fixture.

Fixture adapted from KLEGB/MOOSAS test_airflow_network_json.py (Apache-2.0).
Upstream authors: Jun Xiao, Yihui Li, Hongzhong Chen.
License: https://github.com/KLEGB/MOOSAS/blob/dbf4eb6ed955a1ba9d5052ed0e1d4a9f3411a66c/LICENSE
This is an upstream interoperability probe, never an engineering calculation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

PIN = "dbf4eb6ed955a1ba9d5052ed0e1d4a9f3411a66c"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    upstream, output = args.upstream.resolve(strict=True), args.out.resolve()
    if not upstream.is_relative_to(root) or not output.is_relative_to(root) or output.exists():
        parser.error("Use a repository-local checkout and a new repository-local output directory")
    def git(*args):
        return subprocess.check_output(["git", "-C", str(upstream), *args], text=True).strip()
    if git("rev-parse", "HEAD") != PIN or git("status", "--porcelain"):
        parser.error("Expected exact clean pinned upstream checkout")
    sys.path.insert(0, str(upstream))
    from MoosasPy.simulation.airflow.network import AfnZone, AfnPath, buildNetworkFile
    output.mkdir(parents=True)
    zone = AfnZone(userName="room", temperature=27.0, prjIndex=1, prjName="z001",
                   heatLoad=100.0, volume=30.0, position_x=2.0, position_y=1.5,
                   position_z=1.5, boundary="0 0 4 0 4 3 0 3", level=0.0,
                   levelIndex=1, relHt=1.5, contam={})
    opening = AfnPath(userName="window", prjIndex=1, pathHeight=2.0, pathWidth=1.0,
                      position_x=0.0, position_y=1.5, position_z=1.5,
                      fromZone=-1, toZone=1, pressure=0.0, winType=1,
                      orientation=[1.0, 0.0, 0.0], pathType="glazing", level=0.0,
                      levelIndex=1, relHt=1.5, contam={}, operable=0.5)
    network = output / "network.json"
    buildNetworkFile(pathList=[opening], zoneList=[zone], networkFilePath=str(network))
    libs = upstream / "MoosasPy/libs"
    afn = libs / "moosas_afn/windows-x86_64/bin/MoosasAFN.exe"
    contam = libs / "contam/windows-x86_64/bin/contamx3.exe"
    report = {"upstream_commit": PIN, "fixture_source": "test/test_airflow_network_json.py",
              "scope": "Synthetic native interoperability only; upstream defaults retained",
              "limitations": ["Fixture dimensions and volume are upstream test inputs, not a coherent building model",
                               "Opening coefficients and solver defaults are not sourced project parameters",
                               "No IFC binding, conservation audit, HK checks or engineering acceptance"],
              "design_accepted": False, "simulation_verified": False, "commands": []}
    def run(command):
        record = {"command": [str(x) for x in command],
                  "executable_sha256": hashlib.sha256(Path(command[0]).read_bytes()).hexdigest()}
        try:
            result = subprocess.run(record["command"], cwd=output, stdin=subprocess.DEVNULL,
                                    capture_output=True, text=True, errors="replace", timeout=45)
            record.update(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
        except (OSError, subprocess.TimeoutExpired) as exc:
            record.update(returncode=None, error=str(exc))
        report["commands"].append(record)
        return record.get("returncode") == 0
    project = output / "smoke.prj"
    generated = run([afn, "-p", "smoke", "-d", output, "-s", "0", network])
    report["project_generated"] = generated and project.is_file() and project.stat().st_size > 0
    report["solver_exit_success"] = False
    if report["project_generated"]:
        report["solver_exit_success"] = run([contam, project])
    report["artifacts"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in output.iterdir() if p.is_file()}
    (output / "probe.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("project_generated", "solver_exit_success", "simulation_verified")}))
    return 0 if report["solver_exit_success"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
