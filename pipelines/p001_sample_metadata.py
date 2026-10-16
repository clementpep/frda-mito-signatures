"""P-001 — GSM-level sample metadata for the two seed series (task T-001).

Reads the GEO family SOFT file of each series (allowlisted `ncbi-geo` source, fetched through
`frda.acquire` with a pinned sha256), matches every matrix column to exactly one GSM by title,
keeps every characteristic verbatim, and cross-checks the manifest group of each column against
the GEO characteristics.

uv run python pipelines/p001_sample_metadata.py --out /tmp/p001
"""

from __future__ import annotations

import argparse
import gzip
import re
from pathlib import Path

import numpy as np
from scipy import stats

from frda.acquire import fetch_file
from frda.io import load_matrix
from frda.manifest import Manifest, ManifestFile
from frda.provenance import write_json, write_run

SOFT = {
    "GSE104288": (
        "GSE104288_family.soft.gz",
        "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE104nnn/GSE104288/soft/GSE104288_family.soft.gz",
        "ebcbea0d553d981d38062e66a27fb2baaffef518645afdbc02846284e4e36cb8",
    ),
    "GSE145115": (
        "GSE145115_family.soft.gz",
        "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE145nnn/GSE145115/soft/GSE145115_family.soft.gz",
        "31a4b965090c5e26ca5d0488cb17c9d9c520c336a6f4d435b76c3834f8a8b2b2",
    ),
}

# Expected manifest group, derived only from the GEO characteristics (the cross-check).
GSE104288_GENOTYPE = {"Control": "control", "Friedreich's ataxia": "FRDA"}
GSE145115_LINE = {"GM78": "FRDA", "GM40": "control"}  # title prefix; line not in characteristics
GSE145115_TREATMENT = {
    "untreated": "untreated",
    "DMSO": "DMSO",
    "1 uM compound A-196": "A196_low",
    "5 uM compound A-196": "A196_mid",
    "10 uM compound A-196": "A196_high",
    "10 uM compound SGC2043": "SGC2043",
}
AGE_RE = re.compile(r"^(\d+(?:\.\d+)?) ([dmy])$")
AGE_TO_YEARS = {"d": 1 / 365.25, "m": 1 / 12, "y": 1.0}


def parse_soft(path: Path) -> tuple[list[dict], dict[str, list[str]]]:
    """Return (samples, series_fields). Repeated keys keep file order."""
    samples: list[dict] = []
    series: dict[str, list[str]] = {}
    cur: dict | None = None
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line.startswith("^SAMPLE"):
                cur = {"fields": {}}
                samples.append(cur)
            elif line.startswith("^"):
                cur = None
            elif line.startswith("!Sample_") and cur is not None:
                key, _, val = line[1:].partition(" = ")
                cur["fields"].setdefault(key, []).append(val)
            elif line.startswith("!Series_"):
                key, _, val = line[1:].partition(" = ")
                series.setdefault(key, []).append(val)
    return samples, series


def characteristics(fields: dict[str, list[str]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in fields.get("Sample_characteristics_ch1", []):
        k, sep, v = item.partition(": ")
        if not sep or k in out:
            raise ValueError(f"unparseable or duplicated characteristic {item!r}")
        out[k] = v
    return out


def _fetch_soft(manifest: Manifest) -> Path:
    name, url, sha = SOFT[manifest.id]
    f = ManifestFile(
        name=name,
        url=url,
        sha256=sha,
        content="GEO family SOFT (metadata only)",
        gene_id_column="-",
        gene_id_type="symbol",
        values="metadata",
    )
    path, _ = fetch_file(manifest, f)
    return path


def build_series(dataset: str) -> tuple[dict, dict]:
    df, manifest = load_matrix(dataset)
    soft_path = _fetch_soft(manifest)
    samples, series = parse_soft(soft_path)
    by_title: dict[str, list[dict]] = {}
    for s in samples:
        by_title.setdefault(s["fields"]["Sample_title"][0], []).append(s)
    group_of = {c: g.name for g in manifest.groups for c in g.samples}

    records, problems = [], []
    for col in map(str, df.columns):
        hits = by_title.get(col, [])
        if len(hits) != 1:
            problems.append(f"{col}: {len(hits)} GSM with this title")
            continue
        f = hits[0]["fields"]
        chars = characteristics(f)
        rec = {
            "column": col,
            "gsm": f["Sample_geo_accession"][0],
            "title": f["Sample_title"][0],
            "source_name": f.get("Sample_source_name_ch1", ["not provided"])[0],
            "characteristics": chars,
            "growth_protocol": f.get("Sample_growth_protocol_ch1", ["not provided"])[0],
            "treatment_protocol": f.get("Sample_treatment_protocol_ch1", ["not provided"])[0],
            "manifest_group": group_of.get(col),
        }
        if dataset == "GSE104288":
            rec["expected_group"] = GSE104288_GENOTYPE.get(chars.get("genotype", ""))
            m = AGE_RE.match(chars.get("sampling age", ""))
            rec["age_years"] = float(m.group(1)) * AGE_TO_YEARS[m.group(2)] if m else "not provided"
            rec["sex"] = "not provided"
        else:
            line = GSE145115_LINE.get(col[:4])
            tr = GSE145115_TREATMENT.get(chars.get("treatment", ""))
            if line and tr:
                rec["expected_group"] = (
                    f"{line}_{tr}" if line == "FRDA" or tr in {"untreated", "DMSO"} else None
                )
            else:
                rec["expected_group"] = None
            rec["cell_line_note"] = (
                "cell line not given per sample in GEO; inferred from title prefix "
                "(GM78=GM04078, GM40=GM03440) and the series overall design"
            )
        if rec["expected_group"] != rec["manifest_group"]:
            problems.append(
                f"{col}: manifest group {rec['manifest_group']!r} != GEO-derived "
                f"{rec['expected_group']!r}"
            )
        records.append(rec)

    gsm = [r["gsm"] for r in records]
    declared = {s for g in manifest.groups for s in g.samples}
    checks = {
        "n_matrix_columns": int(df.shape[1]),
        "n_gsm_in_soft": len(samples),
        "n_records": len(records),
        "n_unique_gsm": len(set(gsm)),
        "n_soft_samples_unmatched": len(
            {s["fields"]["Sample_title"][0] for s in samples} - set(map(str, df.columns))
        ),
        "n_manifest_samples_not_in_matrix": len(declared - set(map(str, df.columns))),
        "mismatches": problems,
    }
    bad = (
        problems
        or checks["n_records"] != checks["n_matrix_columns"]
        or checks["n_unique_gsm"] != checks["n_records"]
        or checks["n_soft_samples_unmatched"]
        or checks["n_manifest_samples_not_in_matrix"]
    )
    if bad:
        raise SystemExit(f"{dataset}: metadata reconciliation failed: {checks}")
    out = {
        "dataset": dataset,
        "series_overall_design": series.get("Series_overall_design", []),
        "series_pubmed_id": series.get("Series_pubmed_id", []),
        "series_platform_id": series.get("Series_platform_id", []),
        "data_processing": sorted(
            {d for s in samples for d in s["fields"].get("Sample_data_processing", [])}
        ),
        "checks": checks,
        "samples": records,
    }
    return out, checks


def age_balance(records: list[dict]) -> dict:
    groups: dict[str, list[float]] = {}
    for r in records:
        if r["age_years"] is not None:
            groups.setdefault(r["manifest_group"], []).append(r["age_years"])
    summary = {}
    for g, v in sorted(groups.items()):
        a = np.array(v)
        q1, med, q3 = np.percentile(a, [25, 50, 75])
        summary[g] = {
            "n_with_age": len(v),
            "mean": float(a.mean()),
            "sd": float(a.std(ddof=1)),
            "median": float(med),
            "q1": float(q1),
            "q3": float(q3),
            "min": float(a.min()),
            "max": float(a.max()),
        }
    u = stats.mannwhitneyu(groups["FRDA"], groups["control"], alternative="two-sided")
    welch = stats.ttest_ind(groups["FRDA"], groups["control"], equal_var=False)
    diff = float(np.mean(groups["FRDA"]) - np.mean(groups["control"]))
    return {
        "per_group": summary,
        "mean_difference_FRDA_minus_control_years": diff,
        "mannwhitney_u": float(u.statistic),
        "mannwhitney_p_two_sided": float(u.pvalue),
        "welch_t": float(welch.statistic),
        "welch_p_two_sided": float(welch.pvalue),
        "note": "descriptive balance check, exploratory; not a confirmatory test",
        "sex": {
            "FRDA": "not provided",
            "control": "not provided",
            "note": "GEO gives no sex field; do not guess. Sex can only be inferred from "
            "expression (XIST / Y-linked genes) in T-002, and would then be labelled inferred.",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    inputs, units, outputs = [], {}, []
    for dataset in SOFT:
        data, _ = build_series(dataset)
        if dataset == "GSE104288":
            data["age_sex_balance"] = age_balance(data["samples"])
        fname = f"{dataset}_samples.json"
        write_json(args.out / fname, data)
        outputs.append(fname)
        name, url, sha = SOFT[dataset]
        inputs.append({"dataset": dataset, "file": name, "url": url, "sha256": sha})
        _, manifest = load_matrix(dataset)
        f = manifest.files[0]
        inputs.append({"dataset": dataset, "file": f.name, "sha256": f.sha256 or ""})
        for g in manifest.groups:
            units[f"{dataset}:{g.name}"] = g.independent_units

    write_run(
        args.out,
        pipeline="P-001",
        task="T-001",
        inputs=inputs,
        params={"match_key": "Sample_title == matrix column", "age_unit": "years (d/365.25)"},
        independent_units=units,
        outputs=outputs,
        analysis_kind="qc",
    )


if __name__ == "__main__":
    main()
