"""Tests for the form.idx parser and preset resolver."""
from __future__ import annotations

import pytest

from edgar_research.forms import PRESETS, expand_forms, parse_form_idx

SAMPLE_IDX = """Description:           Master Index of EDGAR Dissemination Feed by Form Type
Last Data Received:    December 31, 2023
Comments:              webmaster@sec.gov
Anonymous FTP:         ftp://ftp.sec.gov/edgar/




Form Type                                                              Company Name                                                  CIK         Date Filed  File Name
---------------------------------------------------------------------------------------------------------------------------------------------
10-K                                                                   APPLE INC                                                     0000320193  2023-11-03  edgar/data/320193/0000320193-23-000106.txt
10-K/A                                                                 WIDGET CORP                                                   0000111111  2023-06-15  edgar/data/111111/0000111111-23-000222.txt
10-Q                                                                   MICROSOFT CORP                                                0000789019  2023-10-24  edgar/data/789019/0000789019-23-000014.txt
DEF 14A                                                                TESLA INC                                                     0001318605  2023-04-28  edgar/data/1318605/0001318605-23-000045.txt
N-CSR                                                                  VANGUARD INDEX FUNDS                                          0000036405  2023-03-15  edgar/data/36405/0000036405-23-000234.txt
N-CSRS                                                                 FIDELITY MAGELLAN FUND                                        0000061397  2023-09-01  edgar/data/61397/0000061397-23-000100.txt
SC 13D                                                                 ACTIVIST HOLDINGS LP                                          0002000000  2023-07-11  edgar/data/2000000/0002000000-23-000001.txt
"""


def test_parse_returns_matching_forms_only():
    entries = parse_form_idx(SAMPLE_IDX, ["10-K"])
    assert len(entries) == 2  # 10-K + 10-K/A (amendments on by default)
    assert {e.form_type for e in entries} == {"10-K", "10-K/A"}


def test_parse_excludes_amendments_when_requested():
    entries = parse_form_idx(SAMPLE_IDX, ["10-K"], include_amendments=False)
    assert [e.form_type for e in entries] == ["10-K"]


def test_parse_handles_multiword_form_types():
    entries = parse_form_idx(SAMPLE_IDX, ["DEF 14A"])
    assert len(entries) == 1
    e = entries[0]
    assert e.form_type == "DEF 14A"
    assert e.company == "TESLA INC"
    assert e.cik == "0001318605"
    assert e.date_filed == "2023-04-28"
    assert e.path.endswith(".txt")
    assert e.accession == "0001318605-23-000045"


def test_parse_extracts_accession_from_path():
    entries = parse_form_idx(SAMPLE_IDX, ["10-Q"])
    assert entries[0].accession == "0000789019-23-000014"


def test_parse_distinguishes_ncsr_from_ncsrs():
    ncsr = parse_form_idx(SAMPLE_IDX, ["N-CSR"], include_amendments=False)
    ncsrs = parse_form_idx(SAMPLE_IDX, ["N-CSRS"], include_amendments=False)
    assert [e.form_type for e in ncsr] == ["N-CSR"]
    assert [e.form_type for e in ncsrs] == ["N-CSRS"]


def test_parse_raises_on_missing_separator():
    with pytest.raises(ValueError):
        parse_form_idx("no separator here\n10-K   ACME   123   2023-01-01  edgar/foo.txt", ["10-K"])


def test_expand_forms_preset_only():
    out = expand_forms(None, "mutual-fund")
    assert out == PRESETS["mutual-fund"]


def test_expand_forms_list_only():
    out = expand_forms(["10-K", "10-Q"], None)
    assert out == ["10-K", "10-Q"]


def test_expand_forms_dedup_preserves_order():
    out = expand_forms(["10-K", "10-Q", "10-K"], None)
    assert out == ["10-K", "10-Q"]


def test_expand_forms_preset_plus_list_merges():
    out = expand_forms(["8-K"], "corporate-annual")
    assert out[: len(PRESETS["corporate-annual"])] == PRESETS["corporate-annual"]
    assert "8-K" in out


def test_expand_forms_rejects_empty():
    with pytest.raises(ValueError):
        expand_forms(None, None)


def test_expand_forms_rejects_unknown_preset():
    with pytest.raises(ValueError):
        expand_forms(None, "not-a-real-preset")
