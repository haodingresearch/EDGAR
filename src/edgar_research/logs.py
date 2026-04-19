"""Download EDGAR daily traffic log files and filter to target accessions.

SEC publishes one zipped CSV per day at
``https://www.sec.gov/dera/data/Public-EDGAR-log-file-data/{year}/Qtr{q}/log{YYYYMMDD}.zip``.
Raw daily files are ~1-2 GB each; this module downloads, filters to the
retail-relevant rows (successful non-crawler non-index hits), intersects with
an accession set, and writes the compact per-day CSV.

Filter logic mirrors the methodology of Ding (2024): keep rows where
``code == 200`` AND ``idx == 0`` AND ``crawler == 0`` AND the requested
file ends in ``.htm`` or ``.txt``.
"""
from __future__ import annotations

import shutil
import zipfile
from collections.abc import Iterable
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from edgar_research.client import SECClient

LOG_URL = "https://www.sec.gov/dera/data/Public-EDGAR-log-file-data/{year}/Qtr{qtr}/log{ymd}.zip"

USE_COLUMNS = [
    "ip",
    "date",
    "time",
    "cik",
    "accession",
    "extention",  # SEC's intentional misspelling
    "code",
    "size",
    "idx",
    "noagent",
    "crawler",
]


def _daterange(start: date, end: date) -> Iterable[date]:
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def _quarter(month: int) -> int:
    return (month - 1) // 3 + 1


def filter_retail_access(df: pd.DataFrame) -> pd.DataFrame:
    """Drop index-file hits, non-200 responses, and declared crawlers.

    Output schema preserves ``ip, date, time, cik, accession, extention, size, noagent``.
    """
    mask = (df["code"] == 200) & (df["idx"] == 0) & (df["crawler"] == 0)
    df = df.loc[mask].copy()
    df.drop(columns=["code", "idx", "crawler"], inplace=True, errors="ignore")
    df["extention"] = df["extention"].astype(str).str[-3:]
    df = df[df["extention"].isin(["htm", "txt"])].copy()
    df.reset_index(drop=True, inplace=True)
    return df


def _read_daily_csv(csv_path: Path) -> pd.DataFrame:
    # Some historical days are missing the ``time`` column — request intersectional cols.
    usecols = [c for c in USE_COLUMNS if c != "time"] + ["time"]
    try:
        return pd.read_csv(csv_path, engine="pyarrow", usecols=lambda c: c in usecols)
    except Exception:
        return pd.read_csv(csv_path, usecols=lambda c: c in usecols, low_memory=False)


def download_and_filter_day(
    client: SECClient,
    day: date,
    target_accessions: set[str],
    out_dir: Path,
    tmp_dir: Path,
) -> Path | None:
    ymd = day.strftime("%Y%m%d")
    out_file = out_dir / f"edgar{ymd}.csv"
    if out_file.exists() and out_file.stat().st_size > 0:
        return out_file

    url = LOG_URL.format(year=day.year, qtr=_quarter(day.month), ymd=ymd)
    zip_path = tmp_dir / f"log{ymd}.zip"

    try:
        client.download(url, zip_path)
    except Exception as e:
        tqdm.write(f"[warn] {ymd} download failed: {e}")
        return None

    csv_path: Path | None = None
    try:
        with zipfile.ZipFile(zip_path) as z:
            csv_name = next((n for n in z.namelist() if n.endswith(".csv")), None)
            if csv_name is None:
                tqdm.write(f"[warn] {ymd} zip contains no CSV")
                return None
            z.extract(csv_name, tmp_dir)
            csv_path = tmp_dir / csv_name

        df = _read_daily_csv(csv_path)
        df = filter_retail_access(df)
        df = df[df["accession"].isin(target_accessions)].reset_index(drop=True)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_file, index=False)
        return out_file
    except Exception as e:
        tqdm.write(f"[warn] {ymd} parse/filter failed: {e}")
        return None
    finally:
        zip_path.unlink(missing_ok=True)
        if csv_path is not None:
            csv_path.unlink(missing_ok=True)


def download_logs_year(
    client: SECClient,
    year: int,
    target_accessions: set[str],
    out_dir: Path | str,
) -> list[Path]:
    if not target_accessions:
        raise ValueError("target_accessions is empty; nothing to filter")

    year_dir = Path(out_dir) / str(year)
    year_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = year_dir / ".tmp"
    tmp_dir.mkdir(exist_ok=True)

    days = list(_daterange(date(year, 1, 1), date(year, 12, 31)))
    results: list[Path] = []
    failed = 0

    try:
        for day in tqdm(days, desc=f"Logs {year}", unit="day"):
            path = download_and_filter_day(client, day, target_accessions, year_dir, tmp_dir)
            if path is not None:
                results.append(path)
            else:
                failed += 1
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    tqdm.write(f"Year {year}: {len(results)} days succeeded, {failed} failed.")
    return results
