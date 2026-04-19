"""Tests for index read/write round-trips."""
from __future__ import annotations

from pathlib import Path

from edgar_research.forms import FilingEntry
from edgar_research.index import accessions_from_index, load_index, write_index


def _fixture_entries() -> list[FilingEntry]:
    return [
        FilingEntry(
            form_type="10-K",
            company="APPLE INC",
            cik="0000320193",
            date_filed="2023-11-03",
            path="edgar/data/320193/0000320193-23-000106.txt",
        ),
        FilingEntry(
            form_type="N-CSR",
            company="VANGUARD INDEX FUNDS",
            cik="0000036405",
            date_filed="2023-03-15",
            path="edgar/data/36405/0000036405-23-000234.txt",
        ),
    ]


def test_write_and_load_roundtrip(tmp_path: Path):
    dest = tmp_path / "sub" / "index.csv"
    entries = _fixture_entries()
    write_index(entries, dest)

    assert dest.exists()
    rows = load_index(dest)
    assert len(rows) == 2
    assert rows[0]["form_type"] == "10-K"
    assert rows[0]["company"] == "APPLE INC"
    assert rows[0]["accession"] == "0000320193-23-000106"
    assert rows[1]["form_type"] == "N-CSR"


def test_accessions_from_index(tmp_path: Path):
    dest = tmp_path / "index.csv"
    write_index(_fixture_entries(), dest)

    accessions = accessions_from_index(dest)
    assert accessions == {
        "0000320193-23-000106",
        "0000036405-23-000234",
    }
