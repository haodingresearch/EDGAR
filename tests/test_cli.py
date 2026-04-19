"""Tests for CLI argument parsing and year-spec flattening."""
from __future__ import annotations

import argparse

import pytest

from edgar_research.cli import _flatten_years, _parse_year_spec, build_parser


def test_parse_single_year():
    assert _parse_year_spec("2023") == [2023]


def test_parse_year_range():
    assert _parse_year_spec("2020-2023") == [2020, 2021, 2022, 2023]


def test_parse_year_range_rejects_descending():
    with pytest.raises(argparse.ArgumentTypeError):
        _parse_year_spec("2023-2020")


def test_flatten_years_dedupes_and_sorts():
    assert _flatten_years(["2023", "2020-2022", "2021"]) == [2020, 2021, 2022, 2023]


def test_parser_requires_subcommand():
    p = build_parser()
    with pytest.raises(SystemExit):
        p.parse_args([])


def test_parser_forms_accepts_preset():
    p = build_parser()
    ns = p.parse_args(
        [
            "forms",
            "--years",
            "2023",
            "--preset",
            "mutual-fund",
            "--out",
            "/tmp/x",
        ]
    )
    assert ns.cmd == "forms"
    assert ns.preset == "mutual-fund"
    assert ns.years == ["2023"]


def test_parser_logs_accepts_index():
    p = build_parser()
    ns = p.parse_args(
        ["logs", "--year", "2017", "--index", "idx.csv", "--out", "/tmp/logs"]
    )
    assert ns.cmd == "logs"
    assert ns.index == "idx.csv"
    assert ns.year == 2017


def test_parser_summarise_takes_path():
    p = build_parser()
    ns = p.parse_args(["summarise", "/tmp/filing.txt", "--focus", "risk"])
    assert ns.path == "/tmp/filing.txt"
    assert ns.focus == "risk"
