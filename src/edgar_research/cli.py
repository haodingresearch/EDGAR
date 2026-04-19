"""Command-line interface for ``edgar-research``.

Subcommands:

* ``forms``       — download filings of chosen form types for chosen years
* ``build-index`` — emit an accession CSV without downloading filings
* ``logs``        — download + filter EDGAR daily traffic logs to an accession set
* ``summarise``   — LLM-powered summary of a single filing (requires extras)

The CLI is intentionally thin; all logic lives in the importable modules.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edgar_research import __version__
from edgar_research.client import SECClient, UserAgentError
from edgar_research.forms import PRESETS, download_filings, expand_forms
from edgar_research.index import accessions_from_index, build_from_sec, write_index
from edgar_research.logs import download_logs_year


def _parse_year_spec(spec: str) -> list[int]:
    spec = spec.strip()
    if "-" in spec:
        lo, hi = spec.split("-", 1)
        a, b = int(lo), int(hi)
        if a > b:
            raise argparse.ArgumentTypeError(f"year range {spec!r} must be ascending")
        return list(range(a, b + 1))
    return [int(spec)]


def _flatten_years(specs: list[str]) -> list[int]:
    years: set[int] = set()
    for s in specs:
        years.update(_parse_year_spec(s))
    return sorted(years)


def _make_client() -> SECClient:
    try:
        return SECClient()
    except UserAgentError as e:
        print(f"error: {e}", file=sys.stderr)
        raise SystemExit(2) from e


def cmd_forms(args: argparse.Namespace) -> int:
    forms = expand_forms(args.forms, args.preset)
    years = _flatten_years(args.years)
    out = Path(args.out)
    with _make_client() as client:
        paths, entries = download_filings(
            client,
            years,
            forms,
            out,
            include_amendments=not args.no_amendments,
            skip_existing=not args.no_skip_existing,
        )
        if args.index:
            write_index(entries, Path(args.index))
            print(f"Index: {args.index} ({len(entries)} entries)")
    print(f"Downloaded {len(paths)} filings to {out}")
    return 0


def cmd_build_index(args: argparse.Namespace) -> int:
    forms = expand_forms(args.forms, args.preset)
    years = _flatten_years(args.years)
    with _make_client() as client:
        entries = build_from_sec(client, years, forms, include_amendments=not args.no_amendments)
    dest = write_index(entries, Path(args.out))
    print(f"Wrote {len(entries)} entries → {dest}")
    return 0


def cmd_logs(args: argparse.Namespace) -> int:
    if args.index:
        accessions = accessions_from_index(Path(args.index))
    elif args.forms or args.preset:
        forms = expand_forms(args.forms, args.preset)
        years_for_index = _flatten_years(args.index_years) if args.index_years else [args.year]
        with _make_client() as client:
            entries = build_from_sec(
                client, years_for_index, forms, include_amendments=not args.no_amendments
            )
        accessions = {e.accession for e in entries}
    else:
        print("error: provide --index or --forms/--preset", file=sys.stderr)
        return 2

    if not accessions:
        print("error: no accessions to filter against", file=sys.stderr)
        return 1

    with _make_client() as client:
        paths = download_logs_year(client, args.year, accessions, Path(args.out))

    print(f"Wrote {len(paths)} daily log CSVs → {args.out}/{args.year}/")
    return 0


def cmd_summarise(args: argparse.Namespace) -> int:
    try:
        from edgar_research.summarise import summarise_filing
    except ImportError as e:
        print(
            "error: summarise requires the 'ai' extra. Install with:\n"
            "    pip install 'edgar-research[ai]'",
            file=sys.stderr,
        )
        return 2 if "google" in str(e) or "anthropic" in str(e) else 1

    summary = summarise_filing(Path(args.path), focus=args.focus)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(summary)
        print(f"Summary written → {out}")
    else:
        print(summary)
    return 0


def _add_form_selectors(p: argparse.ArgumentParser, *, required: bool) -> None:
    group = p.add_argument_group("form selection")
    group.add_argument(
        "--forms",
        nargs="+",
        metavar="FORM",
        help="Form types (quote multi-word forms, e.g. 'DEF 14A')",
    )
    group.add_argument(
        "--preset",
        choices=sorted(PRESETS),
        help="Shortcut group of form types",
    )
    group.add_argument(
        "--no-amendments",
        action="store_true",
        help="Exclude /A amendments (default: include)",
    )
    if required:
        # argparse can't enforce one-of between two optional flags natively; cli checks in handler.
        pass


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="edgar-research",
        description="Download and analyse SEC EDGAR filings and traffic log files.",
        epilog="Set EDGAR_USER_AGENT='Your Name your@email.com' before use "
        "(SEC fair-access policy).",
    )
    p.add_argument("--version", action="version", version=f"edgar-research {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True, metavar="COMMAND")

    # forms
    pf = sub.add_parser(
        "forms",
        help="Download filings of specified form types",
        description="Download SEC EDGAR filings for the given years and form types.",
    )
    pf.add_argument(
        "--years", nargs="+", required=True, metavar="Y[-Y]",
        help="Year(s) or ranges, e.g. 2023 or 2020-2023",
    )
    _add_form_selectors(pf, required=True)
    pf.add_argument("--out", required=True, help="Output directory for downloaded filings")
    pf.add_argument("--index", help="Also write an accession index CSV to this path")
    pf.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="Re-download filings even if present on disk",
    )
    pf.set_defaults(func=cmd_forms)

    # build-index
    pi = sub.add_parser(
        "build-index",
        help="Build an accession index CSV from SEC's full-index (no filing downloads)",
    )
    pi.add_argument("--years", nargs="+", required=True, metavar="Y[-Y]")
    _add_form_selectors(pi, required=True)
    pi.add_argument("--out", required=True, help="Output CSV path")
    pi.set_defaults(func=cmd_build_index)

    # logs
    pl = sub.add_parser(
        "logs",
        help="Download and filter EDGAR daily traffic logs for one year",
    )
    pl.add_argument("--year", type=int, required=True, help="Calendar year of logs to download")
    pl.add_argument("--out", required=True, help="Output directory (year subfolder auto-added)")
    group = pl.add_argument_group("accession source (choose one)")
    group.add_argument("--index", help="Path to accession index CSV")
    _add_form_selectors(pl, required=False)
    pl.add_argument(
        "--index-years",
        nargs="+",
        metavar="Y[-Y]",
        help="Years of filings to index against (default: --year)",
    )
    pl.set_defaults(func=cmd_logs)

    # summarise
    ps = sub.add_parser(
        "summarise",
        help="LLM-powered summary of a single filing (Gemini primary, Claude fallback)",
    )
    ps.add_argument("path", help="Path to a downloaded filing (.txt)")
    ps.add_argument(
        "--focus",
        help="Angle: governance | financial | strategy | risk | free-text",
    )
    ps.add_argument("--out", help="Write summary to this file (default: stdout)")
    ps.set_defaults(func=cmd_summarise)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
