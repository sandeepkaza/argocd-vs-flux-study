# Paper 7 results (kind v1.34, Gitea in-cluster; Argo CD v3.4.5, Flux v2.9.2; snapshot 2026-07-18)

Corpus: 50 synthetic apps (pause) + Online Boutique; target app bumped via
annotation commit; all timings client-observed monotonic, poll 0.25 s.
Sync = commit push → deployment updated (applied) → available (healthy).
Data: results_argocd.csv, results_argocd_tuned.csv, results_flux.csv,
results_flux_tuned.csv. Runner log: argocd-leg.log, p7-rest.log.

## Sync latency (commit → healthy), 10 trials each

| condition | median | range |
|---|---|---|
| Argo CD, defaults (3 min repo poll) | 236.8 s | 180.3–382.7 |
| Argo CD, tuned (timeout.reconciliation=10s) | 41.6 s | 10.4–177.9* |
| Flux, 1 m intervals (GitRepository+Kustomization) | 58.5 s | 7.1–61.5 |
| Flux, tuned (10 s intervals) | 5.6 s | 4.9–10.7 |

*trial 1 (177.9 s) immediately follows controller restart; excluded from
median? NO — median reported over all 10; note in paper.

Findings:
- Defaults comparison: Flux's quickstart intervals (1 m) deliver ~4× faster
  sync than Argo's default 3-min poll. Both are detection-cadence-bound —
  the distribution is ~uniform over the polling interval.
- Tuned-to-parity (both 10 s): Flux reaches ~5.6 s median — near its
  configured cadence — while Argo CD bottoms out at ~41.6 s median despite a
  10 s reconciliation timeout: its refresh/queue machinery imposes a floor
  well above the configured cadence. Tuning inverts the ranking.
- Flux decomposition: detect (artifact revision) → applied gap is
  consistently <1.5 s; the entire latency is detection cadence.

## Drift correction (out-of-band scale 1→3), 5 trials

| engine | corrections (s, in trial order) |
|---|---|
| Argo CD (selfHeal, watch-based) | 0.63, 0.66, 2.30, 14.61, 52.62 |
| Flux (interval reconcile, 1 m) | 63.2, 59.2, 63.2, 64.3, 63.3 |

Findings:
- Argo's watch-based selfHeal corrects in **sub-second** — but repeated
  drift of the same app triggers an escalating anti-flap backoff
  (0.6 s → 52.6 s across five consecutive drifts). Fast but stateful.
- Flux is flatly interval-bound (~62 s at 1 m): slower steady-state, fully
  predictable, no escalation.

## Deletion recovery (deployment deleted), 5 trials

| engine | recreate-to-available (s) |
|---|---|
| Argo CD | 160.2, 302.0, 301.2, 302.1, 300.4 |
| Flux (prune) | 62.8, 59.8, 62.7, 62.2, 58.7 |

Finding — the paper's sharpest asymmetry: Argo CD heals spec drift in
sub-seconds but takes ~300 s (its self-heal retry/backoff cycle) to recreate
a *deleted* resource — a five-minute exposure window inside "self-healing".
Flux treats deletion like any other divergence: fixed at the next reconcile
(~60 s). Engines differ not in "has drift correction" but in WHICH drift
class each corrects quickly.

## Interpretation grid (for the paper)

- Choose by drift model: watch-based instant-but-stateful (Argo) vs
  interval-based flat-and-predictable (Flux).
- Detection cadence is the whole sync story at defaults; tuned floors differ
  by ~8× (5.6 vs 41.6 s).
- All numbers are single-node kind; cloud spot-check pending (AKS) before
  drafting environment-validity claims.

(User validates every number against the CSVs before drafting.)
