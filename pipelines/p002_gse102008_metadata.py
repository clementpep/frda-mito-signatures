"""P-002 — GSM-level sample metadata of the blood cohort GSE102008 (task T-026).

Reads only the header of the GEO series matrix (allowlisted `ncbi-geo` source, fetched through
`frda.acquire` with a pinned sha256), never the expression values. One record per matrix column.

GEO's series matrix writes the `!Sample_characteristics_ch1` lines *compacted*: when a sample lacks
a field, its remaining fields move up a line (e.g. a patient without `gaa2` shows `duration: 55` on
the `gaa2` line). Characteristics are therefore parsed by their `key:` per sample, never by line.

uv run python pipelines/p002_gse102008_metadata.py --out /tmp/p002
"""

from __future__ import annotations

import argparse
import csv
import gzip
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from frda.acquire import fetch_file
from frda.manifest import Manifest, ManifestFile
from frda.provenance import write_json, write_run

DATASET = "GSE102008"
FILE_NAME = "GSE102008_series_matrix.txt.gz"
URL = "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE102nnn/GSE102008/matrix/GSE102008_series_matrix.txt.gz"
SHA256 = "574bc21e377a6552f2329079b9665789b25732b1b93bfec484fa44023e966b45"

NUMERIC = ("batch", "rin", "age", "onset", "duration", "gaa1", "gaa2", "functional stage")
CLINICAL = ("onset", "duration", "gaa1", "gaa2", "functional stage")
STATUSES = ("Patient", "Carrier", "Control")
TITLE_RE = re.compile(r"^(CHOP|UCLA)_(\w+?)_(?:(mo|mom|fa)_)?(Patient|Carrier|Control)_(\d+)(r?)$")
MISSING = "not provided"


def _manifest() -> tuple[Manifest, ManifestFile]:
    """In-memory, metadata-only descriptor (as P-001 does): the series matrix holds Illumina probe
    ids, which the manifest schema cannot express yet (see backlog T-026b)."""
    f = ManifestFile(
        name=FILE_NAME,
        url=URL,
        sha256=SHA256,
        content="GEO series matrix (header read for metadata only)",
        gene_id_column="ID_REF",
        gene_id_type="symbol",
        values="metadata only; expression values are not read by this pipeline",
    )
    m = Manifest.model_validate(
        {
            "id": DATASET,
            "title": "Peripheral blood biomarkers in Friedreich's ataxia",
            "source": "NCBI GEO",
            "accession": DATASET,
            "landing_url": f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={DATASET}",
            "organism": "Homo sapiens",
            "tissue_or_model": "whole blood",
            "assay": "Illumina HT-12 v4 (GPL10558)",
            "publications": [{"pmid": "29790959", "citation": "Nachun D et al. 2018"}],
            "access": {
                "level": "public",
                "terms": "public GEO series",
                "reusable_with_llm_assistant": True,
                "rationale": "metadata pipeline",
            },
            "unit_of_observation": "one individual",
            "independence_note": "one GSM per pidn",
            "groups": [
                {
                    "name": "all",
                    "description": "all",
                    "samples": ["x"],
                    "independent_units": 1,
                    "unit": "donor",
                }
            ],
            "files": [f.model_dump()],
        }
    )
    return m, f


def read_header(path: Path) -> tuple[dict[str, list[str]], dict[str, list[str]], list[str]]:
    """(series fields, sample fields as lists of per-column cells, matrix column header)."""
    series: dict[str, list[str]] = defaultdict(list)
    sample: dict[str, list[list[str]]] = defaultdict(list)
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line.startswith("!series_matrix_table_begin"):
                header = next(csv.reader([fh.readline().rstrip("\n")], delimiter="\t"))
                break
            if line.startswith(("!Series_", "!Sample_")):
                cells = next(csv.reader([line], delimiter="\t"))
                key = cells[0][1:]
                (series if key.startswith("Series_") else sample)[key].append(cells[1:])
    return {k: [c for row in v for c in row] for k, v in series.items()}, sample, header[1:]


def parse_characteristics(rows: list[list[str]], n: int) -> tuple[list[dict[str, str]], dict]:
    out: list[dict[str, str]] = [{} for _ in range(n)]
    lines_used: dict[str, set[int]] = defaultdict(set)
    for li, row in enumerate(rows):
        if len(row) != n:
            raise SystemExit(f"characteristics line {li}: {len(row)} cells for {n} samples")
        for i, cell in enumerate(row):
            if not cell:
                continue
            key, sep, val = cell.partition(": ")
            if not sep:
                raise SystemExit(f"unparseable characteristic {cell!r}")
            if key in out[i]:
                raise SystemExit(f"column {i}: duplicated characteristic {key!r}")
            out[i][key] = val
            lines_used[key].add(li)
    shift = {k: sorted(v) for k, v in sorted(lines_used.items())}
    return out, {"lines_in_which_each_key_appears": shift, "n_lines": len(rows)}


def num(s: str) -> float | None:
    try:
        return float(s)
    except ValueError:
        return None


def desc(values: list[float]) -> dict:
    if not values:
        return {"n": 0}
    s = sorted(values)
    q = statistics.quantiles(s, n=4, method="inclusive") if len(s) > 1 else [s[0]] * 3
    return {
        "n": len(s),
        "mean": statistics.fmean(s),
        "sd": statistics.stdev(s) if len(s) > 1 else None,
        "median": q[1],
        "q1": q[0],
        "q3": q[2],
        "min": s[0],
        "max": s[-1],
    }


def build(path: Path) -> tuple[dict, dict]:
    series, sample, header = read_header(path)
    gsm = list(sample["Sample_geo_accession"][0])
    n = len(gsm)
    titles = sample["Sample_title"][0]
    arrays = sample["Sample_description"][0]
    chars, shift = parse_characteristics(sample["Sample_characteristics_ch1"], n)

    problems: list[str] = []
    if header != gsm:
        problems.append("matrix column header != Sample_geo_accession (order or content)")
    declared = series["Series_sample_id"][0].split()
    if declared != gsm:
        problems.append("Series_sample_id != Sample_geo_accession")
    if any("pidn" not in c for c in chars):
        problems.append("a sample has no pidn")
    if len(set(gsm)) != n:
        problems.append("duplicated GSM")

    records = []
    for i in range(n):
        c, t = chars[i], titles[i]
        m = TITLE_RE.match(t)
        rec: dict = {
            "column": header[i],
            "gsm": gsm[i],
            "title": t,
            "array_id_description": arrays[i],
            "source_name": sample["Sample_source_name_ch1"][0][i],
            "characteristics": c,
        }
        for k in NUMERIC:
            rec[k.replace(" ", "_")] = num(c[k]) if k in c and num(c[k]) is not None else MISSING
            if k in c and num(c[k]) is None:
                problems.append(f"{header[i]}: non-numeric {k}={c[k]!r}")
        rec["pidn"] = c.get("pidn", MISSING)  # a string id: 'LM', '4044_mo' exist
        rec["status"] = c.get("status", MISSING)
        rec["sex"] = c.get("Sex", MISSING)
        rec["site"] = c.get("site", MISSING)
        rec["sample_number"] = c.get("sample number", MISSING)
        if m:
            site, _, rel, status, _, rflag = m.groups()
            rec["title_site"], rec["title_status"] = site, status
            rec["title_run_twice_suffix_r"] = bool(rflag)
            rec["title_relative_token"] = rel or None
            if site != c.get("site") or status != c.get("status"):
                problems.append(
                    f"{header[i]}: title {t!r} disagrees with site/status characteristics"
                )
        else:
            rec["title_site"] = t.split("_")[0]
            rec["title_status"] = next((s for s in STATUSES if s in t), MISSING)
            rec["title_run_twice_suffix_r"] = False
            rec["title_relative_token"] = None
            if rec["title_site"] != c.get("site") or rec["title_status"] != c.get("status"):
                problems.append(
                    f"{header[i]}: title {t!r} disagrees with site/status characteristics"
                )
        records.append(rec)

    unknown_keys = sorted(
        {k for c in chars for k in c}
        - set(NUMERIC)
        - {"pidn", "status", "Sex", "site", "sample number"}
    )
    if unknown_keys:
        problems.append(f"unexpected characteristic keys: {unknown_keys}")

    checks = {
        "n_matrix_columns": len(header),
        "n_gsm": n,
        "n_unique_gsm": len(set(gsm)),
        "n_unique_pidn": len({c.get("pidn") for c in chars}),
        "n_unique_array_ids": len(set(arrays)),
        "problems": problems,
    }
    if problems or not (checks["n_matrix_columns"] == n == checks["n_unique_gsm"]):
        raise SystemExit(f"{DATASET}: reconciliation failed: {checks}")

    by_status = {s: [r for r in records if r["status"] == s] for s in STATUSES}
    tables = {
        "n_per_status": {s: len(v) for s, v in by_status.items()},
        "completeness_per_field_per_status": {
            k.replace(" ", "_"): {
                s: sum(1 for r in v if r[k.replace(" ", "_")] != MISSING)
                for s, v in by_status.items()
            }
            for k in (*CLINICAL, "age", "rin", "batch")
        },
        "site_x_status": {
            site: {s: sum(1 for r in v if r["site"] == site) for s, v in by_status.items()}
            for site in sorted({r["site"] for r in records})
        },
        "batch_x_status": {
            str(int(b)): {s: sum(1 for r in v if r["batch"] == b) for s, v in by_status.items()}
            for b in sorted({r["batch"] for r in records})
        },
        "batch_x_site": {
            str(int(b)): dict(Counter(r["site"] for r in records if r["batch"] == b))
            for b in sorted({r["batch"] for r in records})
        },
        "sex_x_status": {
            sx: {s: sum(1 for r in v if r["sex"] == sx) for s, v in by_status.items()}
            for sx in sorted({r["sex"] for r in records})
        },
        "age_by_status": {
            s: desc([r["age"] for r in v if r["age"] != MISSING]) for s, v in by_status.items()
        },
        "rin_by_status": {
            s: desc([r["rin"] for r in v if r["rin"] != MISSING]) for s, v in by_status.items()
        },
        "age_by_site_status": {
            f"{site}|{s}": desc([r["age"] for r in v if r["site"] == site])
            for site in sorted({r["site"] for r in records})
            for s, v in by_status.items()
        },
        "gaa1_by_status": {
            s: desc([r["gaa1"] for r in v if r["gaa1"] != MISSING]) for s, v in by_status.items()
        },
        "gaa2_by_status": {
            s: desc([r["gaa2"] for r in v if r["gaa2"] != MISSING]) for s, v in by_status.items()
        },
        "functional_stage_by_status": {
            s: desc([r["functional_stage"] for r in v if r["functional_stage"] != MISSING])
            for s, v in by_status.items()
        },
        "onset_by_status": {
            s: desc([r["onset"] for r in v if r["onset"] != MISSING]) for s, v in by_status.items()
        },
        "duration_by_status": {
            s: desc([r["duration"] for r in v if r["duration"] != MISSING])
            for s, v in by_status.items()
        },
        "sample_number_x_status": {
            sn: {s: sum(1 for r in v if r["sample_number"] == sn) for s, v in by_status.items()}
            for sn in sorted({r["sample_number"] for r in records})
        },
        "clinical_fields_present_by_status": {
            s: dict(
                Counter(sum(1 for k in CLINICAL if r[k.replace(" ", "_")] != MISSING) for r in v)
            )
            for s, v in by_status.items()
        },
    }
    # Is duration == age - onset (the paper's definition)? Reported, not enforced.
    diffs = [
        r["age"] - r["onset"] - r["duration"]
        for r in records
        if MISSING not in (r["age"], r["onset"], r["duration"])
    ]
    duration_check = {
        "n_with_age_onset_duration": len(diffs),
        "n_exact": sum(1 for d in diffs if abs(d) < 1e-9),
        "n_negative_duration": sum(
            1 for r in records if r["duration"] != MISSING and r["duration"] < 0
        ),
        "negative_duration_records": [
            {
                "gsm": r["gsm"],
                "pidn": r["pidn"],
                "age": r["age"],
                "onset": r["onset"],
                "duration": r["duration"],
            }
            for r in records
            if r["duration"] != MISSING and r["duration"] < 0
        ],
        "n_abs_diff_le_1": sum(1 for d in diffs if abs(d) <= 1),
        "max_abs_diff": max((abs(d) for d in diffs), default=None),
        "n_with_gaa1_and_gaa2": sum(1 for r in records if MISSING not in (r["gaa1"], r["gaa2"])),
        "n_gaa1_lt_gaa2": sum(
            1 for r in records if MISSING not in (r["gaa1"], r["gaa2"]) and r["gaa1"] < r["gaa2"]
        ),
        "n_gaa1_eq_gaa2": sum(
            1 for r in records if MISSING not in (r["gaa1"], r["gaa2"]) and r["gaa1"] == r["gaa2"]
        ),
        "fields_present_outside_patients": {
            k: sum(
                1 for r in records if r["status"] != "Patient" and r[k.replace(" ", "_")] != MISSING
            )
            for k in CLINICAL
        },
    }
    twice = [
        r for r in records if r["title_run_twice_suffix_r"] or r["sample_number"].endswith("r")
    ]
    relatives = [r for r in records if r["title_relative_token"] or not TITLE_RE.match(r["title"])]
    structure = {
        "run_twice_candidates_title_suffix_r_or_sample_number_r": [
            {
                "gsm": r["gsm"],
                "title": r["title"],
                "status": r["status"],
                "sample_number": r["sample_number"],
            }
            for r in twice
        ],
        "n_titles_with_relative_token_or_nonstandard_form": len(relatives),
        "relative_or_nonstandard_titles": [
            {"gsm": r["gsm"], "title": r["title"], "status": r["status"]} for r in relatives
        ],
        "family_identifier_in_geo": MISSING,
        "pidn_non_numeric": [
            {
                "gsm": r["gsm"],
                "pidn": r["pidn"],
                "title": r["title"],
                "status": r["status"],
                "base_pidn_present_in_cohort": (
                    {
                        "base": r["pidn"].split("_")[0],
                        "status": next(
                            (q["status"] for q in records if q["pidn"] == r["pidn"].split("_")[0]),
                            None,
                        ),
                    }
                    if "_" in r["pidn"]
                    else None
                ),
            }
            for r in records
            if not r["pidn"].isdigit()
        ],
        "pidn_duplicates": [p for p, c in Counter(c.get("pidn") for c in chars).items() if c > 1],
    }
    out_samples = {
        "dataset": DATASET,
        "series_title": series["Series_title"][0],
        "series_overall_design": series["Series_overall_design"],
        "series_pubmed_id": series["Series_pubmed_id"],
        "series_platform_id": series["Series_platform_id"],
        "data_processing": sorted(set(sample["Sample_data_processing"][0])),
        "checks": checks,
        "units": {
            "age": "not stated by GEO",
            "onset": "not stated by GEO",
            "duration": "not stated by GEO (paper: 'disease duration in years'; duration = age - onset in 407/407)",
            "gaa1": "GAA repeat count (not stated by GEO)",
            "gaa2": "GAA repeat count (not stated by GEO)",
            "functional_stage": "ordinal scale (paper: 0-6, FARS-derived)",
            "rin": "RNA integrity number (0-10)",
            "batch": "batch index (label)",
        },
        "characteristics_line_layout": shift,
        "samples": records,
    }
    out_summary = {
        "dataset": DATASET,
        "checks": checks,
        "tables": tables,
        "duration_vs_age_minus_onset": duration_check,
        "structure": structure,
    }
    return out_samples, out_summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    manifest, f = _manifest()
    path, _ = fetch_file(manifest, f)
    samples, summary = build(path)
    write_json(args.out / "GSE102008_samples.json", samples)
    write_json(args.out / "GSE102008_summary.json", summary)
    write_run(
        args.out,
        pipeline="P-002",
        task="T-026a",
        inputs=[{"dataset": DATASET, "file": FILE_NAME, "url": URL, "sha256": SHA256}],
        params={"parse": "characteristics by key per sample (series-matrix lines are compacted)"},
        independent_units={
            f"{DATASET}:{s}": n for s, n in summary["tables"]["n_per_status"].items()
        },
        outputs=["GSE102008_samples.json", "GSE102008_summary.json"],
        analysis_kind="qc",
    )


if __name__ == "__main__":
    main()
