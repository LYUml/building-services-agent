"""Deterministic, conditional single-phase electrical checks. SI inputs only."""
import math


class ProjectError(ValueError):
    pass


def validate(p):
    errors = []
    if not isinstance(p, dict):
        raise ProjectError("project must be an object")
    def need(obj, key, kind, where):
        v = obj.get(key)
        if not isinstance(v, kind) or (kind is str and not v.strip()):
            errors.append(f"{where}.{key}: expected {kind.__name__}")
            return None
        return v
    def num(obj, key, where, low=0, high=None, positive=False):
        v = obj.get(key)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            errors.append(f"{where}.{key}: finite number required")
        elif v < low or (positive and v == low) or (high is not None and v > high):
            errors.append(f"{where}.{key}: out of range")
    need(p, "name", str, "project")
    num(p, "supply_voltage_v", "project", positive=True)
    sources = need(p, "sources", dict, "project") or {}
    for k, v in sources.items():
        if not isinstance(v, str) or not v.strip():
            errors.append(f"sources.{k}: description required")
    circuits = need(p, "circuits", list, "project") or []
    devices = need(p, "devices", list, "project") or []
    ids = {}
    for kind, rows in (("circuits", circuits), ("devices", devices)):
        seen = set()
        for i, row in enumerate(rows):
            w = f"{kind}[{i}]"
            if not isinstance(row, dict):
                errors.append(f"{w}: expected object")
                continue
            key = need(row, "id", str, w)
            if key in seen:
                errors.append(f"{w}: duplicate id {key}")
            seen.add(key)
            source = need(row, "source", str, w)
            if source and source not in sources:
                errors.append(f"{w}: unknown source {source}")
            if kind == "circuits":
                if row.get("phase") not in ("L1", "L2", "L3"):
                    errors.append(f"{w}: phase must be L1/L2/L3")
                for field in ("breaker_a", "tabulated_ampacity_a", "max_vd_percent"):
                    num(row, field, w, positive=True)
                num(row, "correction_factor", w, high=1, positive=True)
                num(row, "demand_factor", w, high=1)
                for field in ("route_length_m", "vd_mv_a_m"):
                    num(row, field, w)
            else:
                need(row, "circuit", str, w)
                num(row, "electrical_kw", w)
                num(row, "power_factor", w, high=1, positive=True)
                for field in ("x_m", "y_m"):
                    num(row, field, w, low=-1e9)
        ids[kind] = seen
    for row in devices:
        if isinstance(row, dict) and isinstance(row.get("circuit"), str) and row.get("circuit") not in ids["circuits"]:
            errors.append(f"device {row.get('id')}: unknown circuit")
    used = {d.get("circuit") for d in devices if isinstance(d, dict) and isinstance(d.get("circuit"), str)}
    for c in circuits:
        if isinstance(c, dict) and c.get("id") not in used:
            errors.append(f"circuit {c.get('id')}: no devices")
    if not circuits or not devices:
        errors.append("at least one populated circuit required")
    if errors:
        raise ProjectError("\n".join(errors))
    return p


def calculate(p):
    validate(p)
    results = []
    phase_va = {x: 0.0 for x in ("L1", "L2", "L3")}
    for c in p["circuits"]:
        ds = [d for d in p["devices"] if d["circuit"] == c["id"]]
        kw = sum(d["electrical_kw"] for d in ds)
        va = sum(d["electrical_kw"] * 1000 / d["power_factor"] for d in ds)
        demand_va = va * c["demand_factor"]
        ib = demand_va / p["supply_voltage_v"]
        iz = c["tabulated_ampacity_a"] * c["correction_factor"]
        vd = c["vd_mv_a_m"] * ib * c["route_length_m"] / 1000
        vd_percent = vd / p["supply_voltage_v"] * 100
        checks = {"ib_le_in": ib <= c["breaker_a"], "in_le_iz": c["breaker_a"] <= iz,
                  "voltage_drop": vd_percent <= c["max_vd_percent"]}
        phase_va[c["phase"]] += demand_va
        results.append(dict(id=c["id"], phase=c["phase"], device_ids=[d["id"] for d in ds],
            connected_electrical_kw=kw, connected_va=va, demand_va=demand_va,
            design_current_a=ib, effective_ampacity_a=iz, voltage_drop_v=vd,
            voltage_drop_percent=vd_percent, checks=checks, source=c["source"]))
    return dict(name=p["name"], circuits=results, phase_demand_va=phase_va,
        device_count=len(p["devices"]), calculated_checks_pass=all(all(c["checks"].values()) for c in results),
        design_accepted=False, pending=["fault disconnection and breaking capacity", "protective coordination",
        "lighting photometry where applicable", "native DWG reopen and drawing count reconciliation",
        "visual PDF review", "source/assumption review"])
