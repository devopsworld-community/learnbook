#!/usr/bin/env python3
"""
check_package.py — slopsquatting gate. Agents hallucinate package names ~20% of the time
(USENIX 2025 via CSA, Apr 2026: 19.7% of 2.23M samples; open-weight models 21.7% vs 5.2% commercial;
43% of hallucinations repeat every run). Attackers register those names. This gate refuses any
dependency that (a) does not exist on the official registry, (b) is younger than --min-age-days,
or (c) has fewer than --min-releases releases. Run it in pre-commit and CI before any install.

    python3 check_package.py pypi requests boto3 fastapi
    python3 check_package.py npm  left-pad @aws-sdk/client-s3
    python3 check_package.py --from-requirements requirements.txt
    python3 check_package.py --from-package-json package.json

Exit 0 = all pass. Exit 1 = at least one dependency refused (prints why).
"""
import argparse, json, re, sys, urllib.request
from datetime import datetime, timezone

UA = {"User-Agent": "tdw-check-package/1.0 (+thedevopsworld)"}


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)


def pypi(name):
    try:
        d = fetch(f"https://pypi.org/pypi/{name}/json")
    except Exception as e:
        return None, f"not on PyPI ({getattr(e, 'code', e)})"
    rels = d.get("releases", {})
    dates = [f["upload_time_iso_8601"] for files in rels.values() for f in files]
    first = min(dates) if dates else None
    return {"name": d["info"]["name"], "first": first, "releases": len(rels),
            "author": d["info"].get("author") or d["info"].get("author_email") or "-",
            "home": d["info"].get("home_page") or d["info"].get("project_url") or "-"}, None


def npm(name):
    try:
        d = fetch(f"https://registry.npmjs.org/{name.replace('/', '%2F')}")
    except Exception as e:
        return None, f"not on npm ({getattr(e, 'code', e)})"
    t = d.get("time", {})
    return {"name": d.get("name"), "first": t.get("created"), "releases": len(d.get("versions", {})),
            "author": (d.get("author") or {}).get("name", "-") if isinstance(d.get("author"), dict) else str(d.get("author", "-")),
            "home": d.get("homepage", "-")}, None


def age_days(iso):
    if not iso:
        return 0
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - dt).days


def parse_requirements(path):
    names = []
    for line in open(path):
        line = line.split("#")[0].strip()
        if not line or line.startswith("-"):
            continue
        names.append(re.split(r"[<>=!~\[; ]", line)[0])
    return names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("registry", nargs="?", choices=["pypi", "npm"])
    ap.add_argument("names", nargs="*")
    ap.add_argument("--from-requirements")
    ap.add_argument("--from-package-json")
    ap.add_argument("--min-age-days", type=int, default=90)
    ap.add_argument("--min-releases", type=int, default=3)
    a = ap.parse_args()

    jobs = []
    if a.from_requirements:
        jobs += [("pypi", n) for n in parse_requirements(a.from_requirements)]
    if a.from_package_json:
        pj = json.load(open(a.from_package_json))
        jobs += [("npm", n) for k in ("dependencies", "devDependencies") for n in pj.get(k, {})]
    if a.registry:
        jobs += [(a.registry, n) for n in a.names]
    if not jobs:
        ap.error("nothing to check")

    bad = 0
    print(f"{'registry':6} {'package':38} {'age_d':>6} {'rels':>5}  verdict")
    for reg, name in jobs:
        info, err = (pypi if reg == "pypi" else npm)(name)
        if err:
            print(f"{reg:6} {name:38} {'-':>6} {'-':>5}  REFUSE  {err}  <- possible hallucinated/slopsquat name"); bad += 1; continue
        age = age_days(info["first"]); reasons = []
        if age < a.min_age_days:
            reasons.append(f"only {age}d old (<{a.min_age_days})")
        if info["releases"] < a.min_releases:
            reasons.append(f"{info['releases']} releases (<{a.min_releases})")
        if info["name"].lower() != name.lower().split("[")[0]:
            reasons.append(f"registry name '{info['name']}' differs from requested")
        verdict = "REFUSE  " + "; ".join(reasons) if reasons else f"ok      author={info['author']}"
        bad += bool(reasons)
        print(f"{reg:6} {name:38} {age:>6} {info['releases']:>5}  {verdict}")
    print(f"\n{bad} refused" if bad else "\nall dependencies pass the existence/age/release gate")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
