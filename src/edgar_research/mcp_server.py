"""MCP server exposing edgar-research as agent-callable tools.

Install the extra first:

    pip install 'edgar-research[mcp,ai]'

Then register with Claude Code (or any MCP-capable agent):

    claude mcp add edgar-research -- edgar-research-mcp

Tools surface the four top-level pipeline stages plus a helper so agents can
discover preset groups without reading the README.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from edgar_research.client import SECClient
from edgar_research.forms import PRESETS, download_filings
from edgar_research.index import accessions_from_index, build_from_sec, write_index
from edgar_research.logs import download_logs_year

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "MCP extras not installed. Run: pip install 'edgar-research[mcp]'"
    ) from exc


mcp = FastMCP("edgar-research")


@mcp.tool()
def list_form_presets() -> dict[str, list[str]]:
    """Return the built-in form-type preset groups."""
    return PRESETS


@mcp.tool()
def download_edgar_filings(
    years: list[int],
    form_types: list[str],
    out_dir: str,
    include_amendments: bool = True,
) -> dict[str, Any]:
    """Download SEC EDGAR filings for the given years and form types.

    Returns the count of downloaded filings and the output directory.
    Filings are named ``{cik}_{accession}.txt`` for easy joining with log data.
    """
    with SECClient() as client:
        paths, entries = download_filings(
            client,
            years,
            form_types,
            Path(out_dir),
            include_amendments=include_amendments,
        )
    return {
        "downloaded": len(paths),
        "matched_in_index": len(entries),
        "out_dir": str(out_dir),
    }


@mcp.tool()
def build_accession_index(
    years: list[int],
    form_types: list[str],
    out_path: str,
    include_amendments: bool = True,
) -> dict[str, Any]:
    """Build an accession CSV from SEC's full-index without downloading filings."""
    with SECClient() as client:
        entries = build_from_sec(client, years, form_types, include_amendments)
    dest = write_index(entries, Path(out_path))
    return {"entries": len(entries), "path": str(dest)}


@mcp.tool()
def download_traffic_logs(year: int, index_csv: str, out_dir: str) -> dict[str, Any]:
    """Download + filter EDGAR daily traffic logs for a year against an accession index."""
    accessions = accessions_from_index(Path(index_csv))
    with SECClient() as client:
        paths = download_logs_year(client, year, accessions, Path(out_dir))
    return {
        "days_written": len(paths),
        "out_dir": f"{out_dir}/{year}",
        "accessions_tracked": len(accessions),
    }


@mcp.tool()
def summarise_edgar_filing(path: str, focus: str | None = None) -> str:
    """Summarise a downloaded EDGAR filing via Gemini (primary) or Claude (fallback)."""
    from edgar_research.summarise import summarise_filing

    return summarise_filing(Path(path), focus=focus)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
