"""Paper 7 harness: GitOps engine sync/drift/failure measurement on kind.

Engine adapters: argocd | flux. All timings client-observed, monotonic clock,
phases recorded from CRD status transitions polled at 0.25 s.

Sync trial:   bump annotation in target app -> git push (t0) ->
              t_detect (engine observes new revision) ->
              t_applied (deployment spec updated in cluster) ->
              t_healthy (deployment available at new generation).
Drift trial:  kubectl scale target deploy to 3 (t0) -> t_reverted (spec back
              to declared replicas) ; delete variant: delete deploy (t0) ->
              t_recreated (deployment exists + available).

Output: appends rows to results_<engine>.csv.
Usage: python harness.py --engine argocd --scenario sync --app app-01 --trials 10
       python harness.py --engine argocd --scenario drift|delete --app app-01 --trials 5
"""

import argparse
import csv
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

CTX = "kind-gitops"
REPO_DIR = Path(os.environ.get("CORPUS_DIR",
    r"C:\Users\Admin\AppData\Local\Temp\claude\C--Users-Admin-Downloads-EB1A"
    r"\ecdb190f-a3f4-4a6b-aaff-ac569de12938\scratchpad\corpus"))
POLL = 0.25


def run(cmd, timeout=120):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def k(*args, timeout=60):
    return run(["kubectl", "--context", CTX, *args], timeout=timeout)


def kjson(*args):
    r = k(*args, "-o", "json")
    return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None


def now():
    return time.perf_counter()


def git_bump(app):
    """Bump the bench/rev annotation; returns (rev_value, commit_sha)."""
    f = REPO_DIR / "apps" / app / "deploy.yaml"
    s = f.read_text(encoding="utf-8")
    import re
    m = re.search(r'bench/rev: "(\d+)"', s)
    rev = int(m.group(1)) + 1
    s = re.sub(r'bench/rev: "\d+"', f'bench/rev: "{rev}"', s)
    f.write_text(s, encoding="utf-8")
    for c in (["add", "-A"],
              ["commit", "-q", "-m", f"bump {app} rev {rev}"],
              ["push", "-q", "origin", "main"]):
        r = run(["git", "-C", str(REPO_DIR)] + c)
        if r.returncode != 0:
            raise SystemExit(f"git failed: {r.stderr[:200]}")
    sha = run(["git", "-C", str(REPO_DIR), "rev-parse", "HEAD"]).stdout.strip()
    return rev, sha


def deploy_state(app, ns):
    d = kjson("-n", ns, "get", "deploy", app)
    if not d:
        return None
    ann = (d["spec"]["template"]["metadata"].get("annotations") or {}).get("bench/rev")
    st = d.get("status", {})
    avail = st.get("availableReplicas", 0) == d["spec"].get("replicas", 1) and \
        st.get("observedGeneration", 0) >= d["metadata"]["generation"]
    return {"rev": ann, "replicas": d["spec"].get("replicas"),
            "available": avail, "generation": d["metadata"]["generation"]}


class Argo:
    ns = "argocd"
    app_ns = "gitops-argocd"

    def detected(self, app, sha):
        a = kjson("-n", self.ns, "get", "application", app)
        if not a:
            return False
        # revision observed by compare/sync machinery
        op = (a.get("status") or {}).get("sync") or {}
        return op.get("revision") == sha

    def name(self):
        return "argocd"


class Flux:
    ns = "flux-system"
    app_ns = "gitops-flux"

    def detected(self, app, sha):
        g = kjson("-n", self.ns, "get", "gitrepository", "corpus")
        if not g:
            return False
        art = ((g.get("status") or {}).get("artifact") or {})
        return sha in (art.get("revision") or "")

    def name(self):
        return "flux"


def sync_trial(eng, app, trial, out):
    ns = eng.app_ns
    pre = deploy_state(app, ns)
    rev, sha = git_bump(app)
    t0 = now()
    t_detect = t_applied = t_healthy = None
    deadline = t0 + 900
    while now() < deadline:
        if t_detect is None and eng.detected(app, sha):
            t_detect = now()
        st = deploy_state(app, ns)
        if st and st["rev"] == str(rev):
            if t_applied is None:
                t_applied = now()
            if st["available"]:
                t_healthy = now()
                break
        time.sleep(POLL)
    row = {
        "trial": trial, "scenario": "sync", "app": app,
        "detect_s": round(t_detect - t0, 2) if t_detect else "",
        "applied_s": round(t_applied - t0, 2) if t_applied else "",
        "healthy_s": round(t_healthy - t0, 2) if t_healthy else "TIMEOUT",
        "wallclock": datetime.now(timezone.utc).isoformat(),
    }
    write(out, row)
    print(f"[{eng.name()}] sync {app} t{trial}: detect={row['detect_s']} "
          f"applied={row['applied_s']} healthy={row['healthy_s']}", flush=True)


def drift_trial(eng, app, trial, out, delete=False):
    ns = eng.app_ns
    if delete:
        k("-n", ns, "delete", "deploy", app, "--wait=false")
    else:
        k("-n", ns, "scale", "deploy", app, "--replicas=3")
    t0 = now()
    t_fixed = None
    deadline = t0 + 900
    while now() < deadline:
        st = deploy_state(app, ns)
        if delete:
            if st and st["available"]:
                t_fixed = now()
                break
        else:
            if st and st["replicas"] == 1:
                t_fixed = now()
                break
        time.sleep(POLL)
    row = {
        "trial": trial, "scenario": "delete" if delete else "drift", "app": app,
        "detect_s": "", "applied_s": "",
        "healthy_s": round(t_fixed - t0, 2) if t_fixed else "TIMEOUT",
        "wallclock": datetime.now(timezone.utc).isoformat(),
    }
    write(out, row)
    print(f"[{eng.name()}] {'delete' if delete else 'drift'} {app} t{trial}: "
          f"corrected={row['healthy_s']}", flush=True)


def write(out, row):
    exists = Path(out).exists()
    with open(out, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["trial", "scenario", "app",
                                          "detect_s", "applied_s", "healthy_s",
                                          "wallclock"])
        if not exists:
            w.writeheader()
        w.writerow(row)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", required=True, choices=["argocd", "flux"])
    ap.add_argument("--scenario", required=True,
                    choices=["sync", "drift", "delete"])
    ap.add_argument("--app", default="app-01")
    ap.add_argument("--trials", type=int, default=10)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    eng = Argo() if args.engine == "argocd" else Flux()
    out = args.out or f"results_{eng.name()}.csv"
    for t in range(1, args.trials + 1):
        if args.scenario == "sync":
            sync_trial(eng, args.app, t, out)
        elif args.scenario == "drift":
            drift_trial(eng, args.app, t, out)
        else:
            drift_trial(eng, args.app, t, out, delete=True)
        time.sleep(3)
    print("done", flush=True)


if __name__ == "__main__":
    main()
