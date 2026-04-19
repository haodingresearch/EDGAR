"""Tests for retail-access filtering and quarter logic."""
from __future__ import annotations

import pandas as pd

from edgar_research.logs import _quarter, filter_retail_access


def test_quarter_boundaries():
    assert _quarter(1) == 1
    assert _quarter(3) == 1
    assert _quarter(4) == 2
    assert _quarter(6) == 2
    assert _quarter(7) == 3
    assert _quarter(9) == 3
    assert _quarter(10) == 4
    assert _quarter(12) == 4


def test_filter_retail_drops_non_200():
    df = pd.DataFrame(
        {
            "ip": ["a", "b", "c"],
            "accession": ["x", "y", "z"],
            "extention": [".htm", ".htm", ".htm"],
            "code": [200, 404, 200],
            "idx": [0, 0, 0],
            "crawler": [0, 0, 0],
        }
    )
    out = filter_retail_access(df)
    assert len(out) == 2
    assert set(out["ip"]) == {"a", "c"}


def test_filter_retail_drops_crawlers():
    df = pd.DataFrame(
        {
            "ip": ["a", "b"],
            "accession": ["x", "y"],
            "extention": [".htm", ".htm"],
            "code": [200, 200],
            "idx": [0, 0],
            "crawler": [0, 1],
        }
    )
    out = filter_retail_access(df)
    assert list(out["ip"]) == ["a"]


def test_filter_retail_drops_index_requests():
    df = pd.DataFrame(
        {
            "ip": ["a", "b"],
            "accession": ["x", "y"],
            "extention": [".htm", ".htm"],
            "code": [200, 200],
            "idx": [1, 0],
            "crawler": [0, 0],
        }
    )
    out = filter_retail_access(df)
    assert list(out["ip"]) == ["b"]


def test_filter_retail_only_keeps_htm_and_txt():
    df = pd.DataFrame(
        {
            "ip": ["a", "b", "c", "d"],
            "accession": ["x", "y", "z", "w"],
            "extention": ["doc.htm", "doc.txt", "doc.xml", "doc.pdf"],
            "code": [200, 200, 200, 200],
            "idx": [0, 0, 0, 0],
            "crawler": [0, 0, 0, 0],
        }
    )
    out = filter_retail_access(df)
    assert sorted(out["extention"].tolist()) == ["htm", "txt"]


def test_filter_retail_normalises_extention_to_three_chars():
    df = pd.DataFrame(
        {
            "ip": ["a"],
            "accession": ["x"],
            "extention": ["verylong.htm"],
            "code": [200],
            "idx": [0],
            "crawler": [0],
        }
    )
    out = filter_retail_access(df)
    assert out["extention"].iloc[0] == "htm"


def test_filter_retail_drops_metadata_columns():
    df = pd.DataFrame(
        {
            "ip": ["a"],
            "accession": ["x"],
            "extention": [".htm"],
            "code": [200],
            "idx": [0],
            "crawler": [0],
        }
    )
    out = filter_retail_access(df)
    for dropped in ("code", "idx", "crawler"):
        assert dropped not in out.columns
