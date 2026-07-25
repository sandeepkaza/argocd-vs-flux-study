"""fig_rig.png -- Paper 7 GitOps measurement rig (diagrams + graphviz).

One git repo, one kind cluster, both engines measured against the same commit
stream. Requires graphviz `dot` on PATH.
Run: python make_arch_diagram.py
"""

from diagrams import Cluster, Diagram, Edge
from diagrams.programming.language import Python
from diagrams.onprem.vcs import Gitea
from diagrams.onprem.gitops import ArgoCD, Flux
from diagrams.k8s.compute import Deployment
from diagrams.generic.storage import Storage

graph_attr = {"dpi": "300", "fontsize": "13", "pad": "0.2", "splines": "spline",
              "nodesep": "0.35", "ranksep": "0.6"}
node_attr = {"fontsize": "11"}

with Diagram("", filename="fig_rig", outformat="png", show=False,
             graph_attr=graph_attr, node_attr=node_attr, direction="LR"):

    harness = Python("harness.py\ncommit push -> poll 0.25s\ndetect / applied / healthy\nns-monotonic timers")

    with Cluster("kind v1.34 (single node, hermetic)"):
        gitea = Gitea("Gitea (in-cluster)\n50 filler apps + boutique\ntarget app bumped by\nannotation commit")

        with Cluster("engine under test (one at a time)"):
            argo = ArgoCD("Argo CD v3.4.5\nwatch-cache + selfHeal\ndefault 3m poll / tuned 10s")
            flux = Flux("Flux v2.9.2\nGitRepository + Kustomization\n1m interval / tuned 10s")

        dep = Deployment("target Deployment\nsync | drift (scale 1->3) |\ndelete recovery")

    out = Storage("results_{argocd,flux}\n{,_tuned}.csv\nsync / drift / delete")

    harness >> Edge(label="commit") >> gitea
    gitea >> argo >> dep
    gitea >> flux >> dep
    dep >> Edge(label="observed state") >> harness
    harness >> out
