#!/usr/bin/env bash
# P7 continuation: tuned Argo condition -> Flux leg (defaults-ish 1m) -> tuned Flux.
set -x
cd "$(dirname "$0")"
K="kubectl --context kind-gitops"

echo "== tuned argo: 10s reconciliation =="
$K -n argocd patch cm argocd-cm --type merge -p '{"data":{"timeout.reconciliation":"10s"}}'
$K -n argocd rollout restart statefulset/argocd-application-controller deploy/argocd-repo-server
$K -n argocd rollout status statefulset/argocd-application-controller --timeout=300s
sleep 45
python harness.py --engine argocd --scenario sync --app app-01 --trials 10 --out results_argocd_tuned.csv

echo "== remove argo =="
$K -n argocd delete application apps --wait=false || true
$K delete ns argocd --wait=true --timeout=600s
$K delete ns gitops-argocd --wait=true --timeout=600s

echo "== install flux v2.9.2 =="
$K apply -f https://github.com/fluxcd/flux2/releases/download/v2.9.2/install.yaml
for d in source-controller kustomize-controller helm-controller notification-controller; do
  $K -n flux-system rollout status deploy/$d --timeout=300s
done
$K apply -f flux.yaml
sleep 120
$K -n flux-system get kustomization apps
$K -n gitops-flux get deploy --no-headers | wc -l

echo "== flux leg (1m intervals) =="
python harness.py --engine flux --scenario sync --app app-01 --trials 10 --out results_flux.csv
python harness.py --engine flux --scenario drift --app app-02 --trials 5 --out results_flux.csv
python harness.py --engine flux --scenario delete --app app-03 --trials 5 --out results_flux.csv

echo "== tuned flux: 10s intervals =="
$K -n flux-system patch gitrepository corpus --type merge -p '{"spec":{"interval":"10s"}}'
$K -n flux-system patch kustomization apps --type merge -p '{"spec":{"interval":"10s"}}'
sleep 30
python harness.py --engine flux --scenario sync --app app-01 --trials 10 --out results_flux_tuned.csv

echo "P7 RUNS COMPLETE"
