"""`frda` command line. Routines and CI only call these subcommands (via make)."""

from __future__ import annotations

import argparse
import json
import sys

from frda import paths


def cmd_fetch(args: argparse.Namespace) -> int:
    from frda.acquire import fetch_file
    from frda.manifest import load_all, manifest_paths
    from frda.yamlio import dump_yaml, load_yaml

    status = 0
    for mpath, m in zip(manifest_paths(), load_all(), strict=True):
        if args.dataset and m.id not in args.dataset:
            continue
        changed = False
        raw = load_yaml(mpath)
        for i, f in enumerate(m.files):
            try:
                path, digest = fetch_file(m, f, record=args.record_checksums, force=args.force)
            except Exception as exc:
                print(f"FAIL {m.id}/{f.name}: {exc}", file=sys.stderr)
                status = 1
                continue
            print(f"OK   {m.id}/{f.name} sha256={digest[:12]}… -> {path.relative_to(paths.ROOT)}")
            if f.sha256 is None and args.record_checksums:
                raw["files"][i]["sha256"] = digest
                raw["files"][i]["size_bytes"] = path.stat().st_size
                changed = True
        if changed:
            dump_yaml(raw, mpath)
            print(f"recorded checksums in {mpath.relative_to(paths.ROOT)} — review and commit")
    return status


def cmd_verify(args: argparse.Namespace) -> int:
    from frda.gates import run_all

    results = run_all(paths.ROOT, require_data=args.require_data)
    if args.json:
        print(json.dumps([r.__dict__ for r in results], indent=2))
    else:
        for r in results:
            print(f"{r.status:<4}  {r.name}")
            for d in r.details:
                print(f"        - {d}")
    failed = [r.name for r in results if r.status == "FAIL"]
    if not args.json:
        print("\nverify: " + ("FAIL (" + ", ".join(failed) + ")" if failed else "PASS"))
    return 1 if failed else 0


def cmd_reproduce(args: argparse.Namespace) -> int:
    from frda.reproduce import load_registry, reproduce_one

    pipelines = load_registry()
    if not pipelines:
        print("reproduce: no registered pipeline yet (pipelines/registry.yaml)")
        return 0
    failed = False
    for p in pipelines:
        if args.pipeline and p.id not in args.pipeline:
            continue
        problems = reproduce_one(p)
        print(f"{'FAIL' if problems else 'PASS'}  {p.id}")
        for pr in problems:
            print(f"        - {pr}")
        failed |= bool(problems)
    return 1 if failed else 0


def cmd_export_hub(args: argparse.Namespace) -> int:
    from frda import hub

    if args.check:
        current = json.loads(paths.HUB_SUMMARY.read_text(encoding="utf-8"))
        ok = hub.stable(current) == hub.stable(hub.build_summary())
        print("hub summary up to date" if ok else "hub summary STALE: run `make hub`")
        return 0 if ok else 1
    print(f"wrote {hub.write().relative_to(paths.ROOT)}")
    return 0


def cmd_autonomy_status(args: argparse.Namespace) -> int:
    from frda.autonomy import status

    st = status()
    if args.json:
        print(json.dumps(st, indent=2))
        return 0
    print(f"WIP {st['wip']}/{st['config']['wip_limit']}")
    for b in st["branches"]:
        print(f"  {b['state']:<20} {b['name']:<28} {b['head'][:8]} {b['subject'][:60]}")
    print(f"next for worker:   {st['next_for_worker']}")
    print(f"next for verifier: {st['next_for_verifier']}")
    for key in ("landing_pending", "needs_human", "stale_landed"):
        if st[key]:
            print(f"{key}: {', '.join(st[key])}")
    return 0


def cmd_task(args: argparse.Namespace) -> int:
    from frda.backlog import load_backlog

    t = load_backlog().task(args.task_id)
    print(json.dumps(t.model_dump(), indent=2, ensure_ascii=False))
    return 0


def cmd_render_paper(args: argparse.Namespace) -> int:
    from frda import paper

    problems = paper.build()
    for p in problems:
        print(f"- {p}")
    print(f"wrote {paper.BUILD.relative_to(paths.ROOT)}")
    return 1 if problems else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="frda")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("fetch", help="download manifest files and verify checksums")
    p.add_argument("--dataset", nargs="*")
    p.add_argument(
        "--record-checksums",
        action="store_true",
        help="bootstrap a NEW manifest: write missing sha256 (never overwrites)",
    )
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_fetch)

    p = sub.add_parser("verify", help="deterministic verification gates")
    p.add_argument(
        "--require-data", action="store_true", help="fail (not skip) when raw data is absent"
    )
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("reproduce", help="re-run pipelines and compare output checksums")
    p.add_argument("--pipeline", nargs="*")
    p.set_defaults(func=cmd_reproduce)

    p = sub.add_parser("export-hub", help="write results/hub/summary.json")
    p.add_argument("--check", action="store_true")
    p.set_defaults(func=cmd_export_hub)

    p = sub.add_parser("autonomy-status", help="state of auto/* and verified/* branches")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_autonomy_status)

    p = sub.add_parser("task", help="print one backlog task")
    p.add_argument("task_id")
    p.set_defaults(func=cmd_task)

    p = sub.add_parser("render-paper", help="render paper/manuscript.md from verified claims")
    p.set_defaults(func=cmd_render_paper)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
