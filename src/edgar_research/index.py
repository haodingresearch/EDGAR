"""Build accession index CSVs used to filter EDGAR traffic logs.

An index row captures enough metadata for the traffic-log filter step to
attribute a log hit to a specific filing: ``accession`` is the join key,
``form_type`` lets downstream analysis bucket by filing type, and
``cik/date_filed/company`` are preserved for convenience.
"""
from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path

from edgar_research.client import SECClient
from edgar_research.forms import FilingEntry, list_filings_years

INDEX_COLUMNS = ["form_type", "cik", "accession", "date_filed", "company", "path"]


def build_from_sec(
    client: SECClient,
    years: Iterable[int],
    forms: Iterable[str],
    include_amendments: bool = True,
) -> list[FilingEntry]:
    """Build an index directly from SEC's form.idx — no filing downloads needed."""
    return list_filings_years(client, years, forms, include_amendments)


def write_index(entries: Iterable[FilingEntry], dest: Path | str) -> Path:
    dest_path = Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with dest_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=INDEX_COLUMNS)
        writer.writeheader()
        for e in entries:
            writer.writerow(
                {
                    "form_type": e.form_type,
                    "cik": e.cik,
                    "accession": e.accession,
                    "date_filed": e.date_filed,
                    "company": e.company,
                    "path": e.path,
                }
            )
    return dest_path


def load_index(src: Path | str) -> list[dict[str, str]]:
    with Path(src).open(newline="") as f:
        return list(csv.DictReader(f))


def accessions_from_index(src: Path | str) -> set[str]:
    return {row["accession"] for row in load_index(src) if row.get("accession")}
