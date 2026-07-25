# Paper 7 — "Reconcile or Watch? An Empirical Comparison of GitOps Engines"

**Genre:** engine comparison (the Paper 2 formula applied to GitOps).
**Venue path:** UCC → IC2E → IEEE Access.
**Gap (web-verified 2026-07-18):** Argo CD vs Flux comparisons are feature
blogs; the one adjacent academic result (Nephio/IBN scenario) measures a
different setting. No controlled study fixes a manifest corpus and measures
sync, drift, and scale behavior on both engines at pinned versions.

## RQs
- RQ1: Sync latency — git commit → cluster converged, decomposed (poll/webhook
  detection → render → apply → healthy), across app sizes (1 / 10 / 50 apps;
  plain YAML vs Helm vs Kustomize render paths).
- RQ2: Drift — out-of-band mutation and deletion: detection time, correction
  time, per engine mechanism (Argo watch-cache + selfHeal vs Flux interval);
  the direct analogue of Paper 2's drift finding.
- RQ3: Failure classes — bad manifest, failing health check, repo
  unreachable: what each engine reports, blocks, or silently skips.
- RQ4: Footprint & API load — controller resource usage and API-server
  request rates at idle and at 50 apps (deployability axis from Paper 2's
  cloud leg).

## Testbed
kind (primary; both engines pinned latest stable) + one managed-cloud spot
check (AKS) for environment validity — the Paper 2 playbook. Corpus: boutique
split into per-service apps + generated filler apps for scale levels. Git
side: Gitea in-cluster (hermetic) or GitHub repo.

## Cost
~$0 local; <$10 cloud spot check.

## Status
- [ ] Corpus repo + commit-driver harness (timestamps from commit SHA to convergence)
- [ ] Runs per engine × app-scale × scenario
- [ ] results.md → user validates → 10pp draft
