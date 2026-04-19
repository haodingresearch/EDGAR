"""Download SEC EDGAR filings of any form type via the public full-index.

The SEC publishes ``form.idx`` per year/quarter at
``https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{q}/form.idx``. Each
row is whitespace-separated and tail-anchored on ``edgar/<path>``, which lets
us parse multi-word form types (``DEF 14A``, ``SC 13D``) robustly.

The original paper repo hard-coded a match on ``N-CSR`` and excluded
``N-CSRS``. This module generalises to any user-supplied form list, plus a
handful of convenience presets.
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from tqdm import tqdm

from edgar_research.client import SECClient

FORM_IDX_URL = "https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{qtr}/form.idx"
FILING_URL = "https://www.sec.gov/Archives/{path}"

PRESETS: dict[str, list[str]] = {
    "corporate-annual": ["10-K", "20-F", "40-F"],
    "corporate-quarterly": ["10-Q", "6-K"],
    "corporate-current": ["8-K"],
    "mutual-fund": ["N-CSR", "N-CSRS", "N-Q", "N-PX", "N-CEN"],
    "proxy": ["DEF 14A", "DEFA14A", "PRE 14A"],
    "insider": ["3", "4", "5"],
    "ownership": ["SC 13D", "SC 13G", "13F-HR", "13F-NT"],
    "registration": ["S-1", "S-3", "S-4", "F-1", "F-3"],
}


@dataclass(frozen=True, slots=True)
class FilingEntry:
    form_type: str
    company: str
    cik: str
    date_filed: str
    path: str  # relative archive path, e.g. "edgar/data/320193/0000320193-23-000106.txt"

    @property
    def accession(self) -> str:
        return Path(self.path).stem

    @property
    def url(self) -> str:
        return FILING_URL.format(path=self.path)


# Matches a form.idx row. Columns are padded with 2+ spaces, so non-greedy
# capture of form + company works even when the form type contains spaces.
_ROW_RE = re.compile(
    r"^"
    r"(?P<form>\S+(?:\s\S+)*?)\s{2,}"
    r"(?P<company>.+?)\s{2,}"
    r"(?P<cik>\d+)\s+"
    r"(?P<date>\d{4}-\d{2}-\d{2})\s+"
    r"(?P<path>edgar/\S+)"
    r"\s*$"
)


def expand_forms(forms: Iterable[str] | None, preset: str | None) -> list[str]:
    """Resolve the effective list of form types to match, deduped, order-preserving."""
    collected: list[str] = []
    if preset:
        if preset not in PRESETS:
            raise ValueError(
                f"Unknown preset {preset!r}. Available: {sorted(PRESETS)}"
            )
        collected.extend(PRESETS[preset])
    if forms:
        collected.extend(forms)
    if not collected:
        raise ValueError("Must specify at least one of --forms or --preset")

    seen: set[str] = set()
    out: list[str] = []
    for f in collected:
        key = f.strip()
        if key and key not in seen:
            seen.add(key)
            out.append(key)
    return out


def _form_matches(row_form: str, wanted: set[str], include_amendments: bool) -> bool:
    form = row_form.strip()
    if include_amendments and form.endswith("/A"):
        form = form[:-2].strip()
    return form in wanted


def parse_form_idx(
    text: str, wanted: Iterable[str], include_amendments: bool = True
) -> list[FilingEntry]:
    """Parse SEC ``form.idx`` text and return matching entries."""
    wanted_set = {w.strip() for w in wanted}
    entries: list[FilingEntry] = []

    lines = text.splitlines()
    # Skip preamble up to the dashed separator row
    start = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and set(stripped) == {"-"}:
            start = i + 1
            break
    if start is None:
        raise ValueError("form.idx: could not find header separator")

    for line in lines[start:]:
        if not line.strip():
            continue
        m = _ROW_RE.match(line)
        if not m:
            continue
        if not _form_matches(m["form"], wanted_set, include_amendments):
            continue
        entries.append(
            FilingEntry(
                form_type=m["form"].strip(),
                company=m["company"].strip(),
                cik=m["cik"],
                date_filed=m["date"],
                path=m["path"],
            )
        )
    return entries


def list_filings(
    client: SECClient,
    year: int,
    quarter: int,
    forms: Iterable[str],
    include_amendments: bool = True,
) -> list[FilingEntry]:
    url = FORM_IDX_URL.format(year=year, qtr=quarter)
    resp = client.get(url)
    return parse_form_idx(resp.text, forms, include_amendments)


def list_filings_years(
    client: SECClient,
    years: Iterable[int],
    forms: Iterable[str],
    include_amendments: bool = True,
) -> list[FilingEntry]:
    all_entries: list[FilingEntry] = []
    forms = list(forms)
    years_list = list(years)
    for year in years_list:
        for qtr in range(1, 5):
            try:
                all_entries.extend(list_filings(client, year, qtr, forms, include_amendments))
            except Exception as e:
                tqdm.write(f"[warn] index {year} Q{qtr}: {e}")
    return all_entries


def download_filings(
    client: SECClient,
    years: Iterable[int],
    forms: Iterable[str],
    out_dir: Path | str,
    include_amendments: bool = True,
    skip_existing: bool = True,
) -> tuple[list[Path], list[FilingEntry]]:
    """Download all filings matching the criteria.

    Returns a (downloaded_paths, all_entries) pair so callers can also emit an
    index CSV from the same pass.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    entries = list_filings_years(client, years, forms, include_amendments)
    if not entries:
        tqdm.write("No filings matched the requested forms/years.")
        return [], []

    tqdm.write(f"Found {len(entries)} filings; downloading to {out}")

    downloaded: list[Path] = []
    for entry in tqdm(entries, desc="Filings", unit="filing"):
        dest = out / f"{entry.cik}_{entry.accession}.txt"
        if skip_existing and dest.exists() and dest.stat().st_size > 0:
            downloaded.append(dest)
            continue
        try:
            client.download(entry.url, dest)
            downloaded.append(dest)
        except Exception as e:
            tqdm.write(f"[err] {entry.accession}: {e}")
    return downloaded, entries
