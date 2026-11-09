"""P-003 — Quality control of the two seed matrices (task T-002).

Decision rules, fixed BEFORE looking at any result (see autonomy/runs/*-worker-T-002.md):
  * values: log2(x + 1) of the published normalised matrix; genes kept = median across samples >= 10;
  * sample-sample similarity: Spearman correlation on the kept genes; per-sample score = median
    correlation to the other samples of the same series;
  * outlier: score < Q1 - 3*IQR of the scores of the series (flag only, nothing is removed);
  * sex (inferred, never declared by GEO): Y-score = mean log2(x+1) of RPS4Y1, DDX3Y, KDM5D, UTY,
    EIF1AY; male if >= 3, female if < 1, "ambiguous" otherwise; XIST reported next to it;
  * PCA on centred log2 values of the kept genes (SVD, sign fixed so the largest |loading| is > 0).

uv run python pipelines/p003_qc.py --out /tmp/p003
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

from frda.io import load_matrix  # noqa: E402
from frda.provenance import write_json, write_run  # noqa: E402

MIN_MEDIAN = 10.0
IQR_K = 3.0
MALE_MIN, FEMALE_MAX = 3.0, 1.0
Y_GENES = ["RPS4Y1", "DDX3Y", "KDM5D", "UTY", "EIF1AY"]
# Ensembl gene ids of the sex genes (for GSE145115, indexed by Ensembl id). Ids are not
# asserted from memory alone: the report checks the Y/XIST pattern is internally coherent.
ENSEMBL = {
    "XIST": "ENSG00000229807",
    "RPS4Y1": "ENSG00000129824",
    "DDX3Y": "ENSG00000067048",
    "KDM5D": "ENSG00000012817",
    "UTY": "ENSG00000183878",
    "EIF1AY": "ENSG00000198692",
}
DATASETS = ["GSE104288", "GSE145115"]


def sex_genes(df: pd.DataFrame) -> dict[str, str]:
    out = {}
    for g, ens in ENSEMBL.items():
        for key in (g, ens):
            if key in df.index:
                out[g] = key
                break
    return out


def pca(x: np.ndarray, k: int = 5) -> tuple[np.ndarray, np.ndarray]:
    """x = samples x genes (already log). Returns (scores samples x k, explained variance ratio)."""
    xc = x - x.mean(axis=0, keepdims=True)
    u, s, vt = np.linalg.svd(xc, full_matrices=False)
    k = min(k, len(s))
    for i in range(k):
        if vt[i, np.argmax(np.abs(vt[i]))] < 0:
            vt[i] = -vt[i]
            u[:, i] = -u[:, i]
    var = s**2 / np.sum(s**2)
    return u[:, :k] * s[:k], var[:k]


def qc_dataset(dataset: str, out: Path, ages: dict[str, float]) -> tuple[dict, list[str]]:
    df, manifest = load_matrix(dataset)
    cols = list(map(str, df.columns))
    group_of = {c: g.name for g in manifest.groups for c in g.samples}
    logd = np.log2(df + 1.0)
    kept = df.index[df.median(axis=1) >= MIN_MEDIAN]
    lk = logd.loc[kept]

    corr = lk.corr(method="spearman")
    cm = corr.to_numpy()
    n = len(cols)
    med = np.array([np.median(np.delete(cm[i], i)) for i in range(n)])
    q1, q3 = np.percentile(med, [25, 75])
    thr = q1 - IQR_K * (q3 - q1)
    flagged = [cols[i] for i in range(n) if med[i] < thr]

    scores, var = pca(lk.to_numpy().T)
    # sex
    sg = sex_genes(df)
    ycols = [sg[g] for g in Y_GENES if g in sg]
    yscore = logd.loc[ycols].mean(axis=0)
    xist = (
        logd.loc[sg["XIST"]] if "XIST" in sg else None
    )  # absent from the matrix -> reported as null
    sex = {}
    for c in cols:
        y = float(yscore[c])
        sex[c] = "male" if y >= MALE_MIN else "female" if y < FEMALE_MAX else "ambiguous"

    samples = {}
    grp_l = [group_of[c] for c in cols]
    for i, c in enumerate(cols):
        samples[c] = {
            "group": group_of[c],
            "median_spearman_to_others": float(med[i]),
            "outlier_flag": c in flagged,
            "library_sum": float(df[c].sum()),
            "genes_detected_gt0": int((df[c] > 0).sum()),
            "y_score": float(yscore[c]),
            "xist_log2": float(xist[c]) if xist is not None else None,
            "median_spearman_same_group": (
                float(np.median([cm[i, j] for j in range(n) if j != i and grp_l[j] == grp_l[i]]))
                if grp_l.count(grp_l[i]) > 1
                else None
            ),
            "inferred_sex": sex[c],
            "pc": {f"PC{j + 1}": float(scores[i, j]) for j in range(scores.shape[1])},
        }
        if c in ages:
            samples[c]["age_years"] = ages[c]

    # PC associations (descriptive): group, inferred sex, age
    assoc = {}
    grp = np.array([group_of[c] for c in cols])
    sx = np.array([sex[c] for c in cols])
    for j in range(scores.shape[1]):
        row = {"variance_explained": float(var[j])}
        ug = sorted(set(grp))
        if len(ug) > 1:
            row["kruskal_p_group"] = float(stats.kruskal(*[scores[grp == g, j] for g in ug]).pvalue)
        us = sorted(set(sx) - {"ambiguous"})
        if len(us) == 2:
            row["mannwhitney_p_inferred_sex"] = float(
                stats.mannwhitneyu(
                    scores[sx == us[0], j], scores[sx == us[1], j], alternative="two-sided"
                ).pvalue
            )
        if ages:
            a = np.array([ages[c] for c in cols])
            rho = stats.spearmanr(scores[:, j], a)
            row["spearman_rho_age"] = float(rho.statistic)
            row["spearman_p_age"] = float(rho.pvalue)
        assoc[f"PC{j + 1}"] = row

    res = {
        "dataset": dataset,
        "n_samples": n,
        "n_genes_total": int(df.shape[0]),
        "n_genes_kept_median_ge_10": int(len(kept)),
        "outlier_rule": {
            "score": "median Spearman correlation to the other samples (log2(x+1), kept genes)",
            "threshold": float(thr),
            "q1": float(q1),
            "q3": float(q3),
            "k": IQR_K,
            "flagged": flagged,
        },
        "sex_check": {
            "genes_found": sg,
            "xist_in_matrix": xist is not None,
            "rule": f"y_score = mean log2(x+1) of {Y_GENES}; male >= {MALE_MIN}, "
            f"female < {FEMALE_MAX}, else ambiguous",
            "counts": {s: int((sx == s).sum()) for s in ["male", "female", "ambiguous"]},
            "by_group": {
                g: {s: int(((grp == g) & (sx == s)).sum()) for s in ["male", "female", "ambiguous"]}
                for g in sorted(set(grp))
            },
        },
        "pca_associations": assoc,
        "library_sum_range": [
            float(min(s["library_sum"] for s in samples.values())),
            float(max(s["library_sum"] for s in samples.values())),
        ],
        "samples": samples,
    }

    # outputs
    corr_df = pd.DataFrame(cm, index=cols, columns=cols)
    corr_df.round(6).to_csv(out / f"{dataset}_spearman.csv")
    pc_df = pd.DataFrame(scores, index=cols, columns=[f"PC{j + 1}" for j in range(scores.shape[1])])
    pc_df["group"] = [group_of[c] for c in cols]
    pc_df.round(5).to_csv(out / f"{dataset}_pca.csv")

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    cmap = plt.get_cmap("tab10")
    for gi, g in enumerate(sorted(set(grp))):
        m = grp == g
        axes[0].scatter(scores[m, 0], scores[m, 1], label=g, color=cmap(gi % 10), s=28)
    for i, c in enumerate(cols):
        if c in flagged:
            axes[0].annotate(c, (scores[i, 0], scores[i, 1]), fontsize=7)
    axes[0].set_xlabel(f"PC1 ({var[0]:.1%})")
    axes[0].set_ylabel(f"PC2 ({var[1]:.1%})")
    axes[0].legend(fontsize=6)
    axes[0].set_title(f"{dataset} PCA (log2, kept genes)")
    order = np.argsort(grp, kind="stable")
    im = axes[1].imshow(cm[np.ix_(order, order)], vmin=float(cm.min()), vmax=1.0, cmap="viridis")
    axes[1].set_title("Spearman (ordered by group)")
    axes[1].set_xticks([])
    axes[1].set_yticks([])
    fig.colorbar(im, ax=axes[1], fraction=0.046)
    fig.tight_layout()
    fig.savefig(out / f"{dataset}_qc.png", dpi=100, metadata={"Software": None})
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.scatter(xist.to_numpy() if xist is not None else np.zeros(n), yscore.to_numpy(), s=24)
    ax.axhline(MALE_MIN, ls=":", c="grey")
    ax.axhline(FEMALE_MAX, ls=":", c="grey")
    ax.set_xlabel("XIST log2(x+1)" if xist is not None else "(XIST absent from matrix)")
    ax.set_ylabel("Y-score")
    ax.set_title(f"{dataset} sex genes")
    fig.tight_layout()
    fig.savefig(out / f"{dataset}_sex.png", dpi=100, metadata={"Software": None})
    plt.close(fig)

    files = [
        f"{dataset}_spearman.csv",
        f"{dataset}_pca.csv",
        f"{dataset}_qc.png",
        f"{dataset}_sex.png",
    ]
    return res, files


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    import json

    meta = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "results/P-001-sample-metadata/GSE104288_samples.json"
        ).read_text(encoding="utf-8")
    )
    ages = {
        r["column"]: float(r["age_years"])
        for r in meta["samples"]
        if isinstance(r["age_years"], int | float)
    }

    outputs, inputs, units = [], [], {}
    for ds in DATASETS:
        res, files = qc_dataset(ds, args.out, ages if ds == "GSE104288" else {})
        write_json(args.out / f"{ds}_qc.json", res)
        outputs += [f"{ds}_qc.json", *files]
        _, m = load_matrix(ds)
        inputs.append({"dataset": ds, "file": m.files[0].name, "sha256": m.files[0].sha256 or ""})
        for g in m.groups:
            units[f"{ds}:{g.name}"] = g.independent_units
    inputs.append(
        {
            "dataset": "GSE104288",
            "file": "results/P-001-sample-metadata/GSE104288_samples.json",
            "sha256": "",
        }
    )
    write_run(
        args.out,
        pipeline="P-003",
        task="T-002",
        inputs=inputs,
        params={
            "min_median": MIN_MEDIAN,
            "iqr_k": IQR_K,
            "male_min": MALE_MIN,
            "female_max": FEMALE_MAX,
            "y_genes": Y_GENES,
            "transform": "log2(x+1)",
            "similarity": "spearman",
        },
        independent_units=units,
        outputs=outputs,
        analysis_kind="qc",
    )


if __name__ == "__main__":
    main()
