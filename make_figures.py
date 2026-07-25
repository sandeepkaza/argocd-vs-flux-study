"""Paper 7 figures (vector PDF, IEEE single-column 3.5in).

Fig 1 (fig_sync.pdf): sync latency (commit->healthy), defaults vs tuned, both
      engines -- carries the ranking inversion.
Fig 2 (fig_drift.pdf): drift correction over 5 consecutive drifts -- Argo's
      sub-second-then-escalating-backoff vs Flux's flat interval.
Fig 3 (fig_delete.pdf): deletion recovery -- the ~300s vs ~60s asymmetry.

Reads results_*.csv. Run: python make_figures.py
"""

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
ARGO, FLUX = "#EF7B45", "#1F6FEB"   # Argo orange-ish, Flux blue
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#d9d8d3"

plt.rcParams.update({
    "font.size": 7.5, "axes.labelsize": 7.5, "axes.titlesize": 8,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7,
    "font.family": "serif", "axes.edgecolor": MUTED, "axes.linewidth": 0.6,
    "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK,
    "axes.labelcolor": INK, "pdf.fonttype": 42,
})


def col(path, scenario, field="healthy_s"):
    out = []
    for r in csv.DictReader(open(HERE / path, encoding="utf-8")):
        if r["scenario"] == scenario and r.get(field):
            out.append(float(r[field]))
    return out


def med(xs):
    xs = sorted(xs)
    n = len(xs)
    return (xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2) if xs else float("nan")


# ---------- Fig 1: sync latency ----------
sync = {
    "Argo\ndefault": (col("results_argocd.csv", "sync"), ARGO, ""),
    "Flux\n1 m": (col("results_flux.csv", "sync"), FLUX, ""),
    "Argo\ntuned 10s": (col("results_argocd_tuned.csv", "sync"), ARGO, "///"),
    "Flux\ntuned 10s": (col("results_flux_tuned.csv", "sync"), FLUX, "///"),
}
fig, ax = plt.subplots(figsize=(3.5, 2.4))
labels = list(sync)
xs = range(len(labels))
for i, k in enumerate(labels):
    data, c, h = sync[k]
    ax.scatter([i] * len(data), data, s=14, color=c, alpha=0.5, zorder=3,
               edgecolor="none")
    m = med(data)
    ax.plot([i - 0.28, i + 0.28], [m, m], color=c, linewidth=1.8, zorder=4)
    ax.annotate(f"{m:.1f}", (i + 0.30, m), fontsize=6.3, color=MUTED, va="center")
ax.set_yscale("log")
ax.set_xticks(list(xs), labels, fontsize=6.6)
ax.set_ylabel("Commit $\\rightarrow$ healthy (s, log)")
ax.axvline(1.5, color=MUTED, linewidth=0.5, linestyle=":")
ax.annotate("defaults", (0.5, ax.get_ylim()[1] * 0.5), ha="center", fontsize=6, color=MUTED)
ax.annotate("tuned to 10 s", (2.5, ax.get_ylim()[1] * 0.5), ha="center", fontsize=6, color=MUTED)
ax.spines[["top", "right"]].set_visible(False)
ax.yaxis.grid(True, linewidth=0.3, color=GRID)
ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig("fig_sync.pdf")
print("fig_sync.pdf")

# ---------- Fig 2: drift correction ----------
argo_drift = col("results_argocd.csv", "drift")
flux_drift = col("results_flux.csv", "drift")
fig, ax = plt.subplots(figsize=(3.5, 2.2))
x = range(1, 6)
ax.plot(x, argo_drift, "o-", color=ARGO, linewidth=1.4, label="Argo CD (selfHeal, watch)")
ax.plot(x, flux_drift, "s-", color=FLUX, linewidth=1.4, label="Flux (interval 1 m)")
for xi, y in zip(x, argo_drift):
    ax.annotate(f"{y:.2g}", (xi, y), fontsize=6, color=MUTED, va="bottom")
ax.set_yscale("log")
ax.set_xticks(list(x))
ax.set_xlabel("Consecutive drift # (same app)")
ax.set_ylabel("Correction time (s, log)")
ax.set_title("Argo: sub-second then anti-flap backoff", fontsize=6.8)
ax.spines[["top", "right"]].set_visible(False)
ax.grid(True, linewidth=0.3, color=GRID)
ax.set_axisbelow(True)
ax.legend(frameon=False, loc="center left", fontsize=6.3)
fig.tight_layout()
fig.savefig("fig_drift.pdf")
print("fig_drift.pdf")

# ---------- Fig 3: deletion recovery ----------
argo_del = col("results_argocd.csv", "delete")
flux_del = col("results_flux.csv", "delete")
fig, ax = plt.subplots(figsize=(3.5, 2.1))
w = 0.35
x = range(1, 6)
ax.bar([i - w / 2 for i in x], argo_del, w, color=ARGO, label=f"Argo CD (med {med(argo_del):.0f}s)")
ax.bar([i + w / 2 for i in x], flux_del, w, color=FLUX, hatch="///", edgecolor="white",
       linewidth=0.3, label=f"Flux prune (med {med(flux_del):.0f}s)")
ax.set_xticks(list(x))
ax.set_xlabel("Trial")
ax.set_ylabel("Recreate $\\rightarrow$ available (s)")
ax.set_title("deleted resource: ~5-min Argo exposure vs ~60 s Flux", fontsize=6.6)
ax.spines[["top", "right"]].set_visible(False)
ax.yaxis.grid(True, linewidth=0.3, color=GRID)
ax.set_axisbelow(True)
ax.legend(frameon=False, loc="center right", fontsize=6.5)
fig.tight_layout()
fig.savefig("fig_delete.pdf")
print("fig_delete.pdf")

# ---------- Fig 4: behavior fingerprint (all scenarios, both engines) ----------
scen = ["sync\n(tuned 10s)", "drift #1\n(first)", "drift #5\n(sustained)", "deletion"]
argo_vals = [med(col("results_argocd_tuned.csv", "sync")), argo_drift[0], argo_drift[-1], med(argo_del)]
flux_vals = [med(col("results_flux_tuned.csv", "sync")), med(flux_drift), med(flux_drift), med(flux_del)]
fig, ax = plt.subplots(figsize=(3.5, 2.3))
x = range(len(scen))
w = 0.38
b1 = ax.bar([i - w / 2 for i in x], argo_vals, w, color=ARGO, label="Argo CD")
b2 = ax.bar([i + w / 2 for i in x], flux_vals, w, color=FLUX, hatch="///",
            edgecolor="white", linewidth=0.3, label="Flux")
for bars in (b1, b2):
    for r in bars:
        ax.annotate(f"{r.get_height():.2g}", (r.get_x() + r.get_width() / 2, r.get_height()),
                    ha="center", va="bottom", fontsize=6, color=MUTED)
ax.set_yscale("log")
ax.set_xticks(list(x), scen, fontsize=6.4)
ax.set_ylabel("Time to converge (s, log)")
ax.set_title("who wins flips scenario to scenario", fontsize=6.8)
ax.spines[["top", "right"]].set_visible(False)
ax.yaxis.grid(True, linewidth=0.3, color=GRID)
ax.set_axisbelow(True)
ax.legend(frameon=False, loc="upper left", fontsize=6.5)
fig.tight_layout()
fig.savefig("fig_fingerprint.pdf")
print("fig_fingerprint.pdf")

print("\n[check] sync med: "
      f"Argo-def {med(sync['Argo\ndefault'][0]):.1f} "
      f"Flux-1m {med(sync['Flux\n1 m'][0]):.1f} "
      f"Argo-tuned {med(sync['Argo\ntuned 10s'][0]):.1f} "
      f"Flux-tuned {med(sync['Flux\ntuned 10s'][0]):.1f}")
print(f"[check] delete med Argo {med(argo_del):.1f} Flux {med(flux_del):.1f}")
