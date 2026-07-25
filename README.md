# gitops-engine-study

Companion artifact for the paper **"Reconcile or Watch? An Empirical Comparison of the Argo CD and Flux GitOps Engines"**.

Controlled comparison of Argo CD vs Flux: sync latency, drift correction, and deletion recovery, with per-trial data at pinned engine versions.

## What's here

`results_*.csv` — per-trial sync/drift/deletion timings for both engines (defaults and tuned). `make_figures.py` — regenerates all figures.

## Reproduce

Requires Python 3 (plus, per paper, Docker/kind/a GPU host — see the paper's
Method section). Every number in the paper is regenerated from the committed
data by:

```bash
python3 make_figures.py   # regenerates every figure from results_*.csv
```

Each stage writes its intermediate data, so the path from raw measurement to
every reported figure is inspectable without re-running the measurement.

## Citation

See `CITATION.cff`. A DOI will be added after Zenodo archival. Venue path:
UCC -> IC2E -> IEEE Access.

## License

MIT (`LICENSE`). Author: Venkata Sandeep Chowdary Kaza <sandeep.kaza@gmail.com>, ORCID 0009-0001-9454-8995.

## AI-assistance disclosure

AI-assisted scripting and editing (Anthropic Claude) was employed under the
author's direction; the author defined the research questions, designed the
method, ran the measurements, and validated every reported number.
