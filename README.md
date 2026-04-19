# edgar-research

> Download SEC EDGAR filings of any form type, filter daily traffic logs against those filings, and summarise them with an LLM — a Python toolkit that follows SEC's EDGAR fair-access policy. Usable as a CLI, an MCP server for AI agents, or a Claude Code skill. Generalises the methodology from **Ding (2024), _Retail Investor Attention and Mutual Fund Performance: Evidence from EDGAR Log Files_** ([SSRN 4992233](https://ssrn.com/abstract=4992233)) to every form type EDGAR publishes.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)

Hao Ding · University of Oxford · [dinghao.co.uk](https://dinghao.co.uk)

---

## What this gives you

1. **`forms`** — download filings of any form type (10-K, 10-Q, 8-K, N-CSR, DEF 14A, 13F-HR, SC 13D, S-1, …) for any year range.
2. **`build-index`** — produce an accession-level CSV from SEC's public full-index without downloading filings.
3. **`logs`** — download the daily EDGAR traffic log, filter to retail-relevant access, and join against an accession set. Days are cached locally so you can resume a year half-way through.
4. **`summarise`** — LLM-powered summary of a single filing (Gemini first, Claude fallback).
5. **MCP server + Claude Skill** — everything above exposed as agent-callable tools.

---

## Install

```bash
git clone https://github.com/haodingresearch/EDGAR.git
cd EDGAR
pip install -e .                # core (forms, logs, build-index)
pip install -e '.[ai]'          # adds the summarise command
pip install -e '.[mcp,ai]'      # adds the MCP server
pip install -e '.[dev]'         # pytest, ruff, responses (for contributors)
```

Requires Python 3.10+.

## One-time setup

SEC's fair-access policy requires every automated request to declare a
contact. Set this once per shell:

```bash
export EDGAR_USER_AGENT="Your Full Name your@email.com"
```

For `summarise`, also set **one of**:

```bash
export GEMINI_API_KEY=...          # preferred (free tier)
export ANTHROPIC_API_KEY=...       # fallback
```

---

## Quickstart

**Download Apple-and-peers 10-K filings for 2023:**

```bash
edgar-research forms --years 2023 --forms 10-K --out ./data/filings
```

**Reproduce the paper's mutual-fund dataset (N-CSR / N-CSRS for 2020-2023) _and_ keep an accession index for downstream log filtering:**

```bash
edgar-research forms \
  --years 2020-2023 \
  --preset mutual-fund \
  --out ./data/filings \
  --index ./data/ncsr_index.csv
```

**Filter the 2023 daily traffic logs to only rows that touched those filings:**

```bash
edgar-research logs \
  --year 2023 \
  --index ./data/ncsr_index.csv \
  --out ./data/logs
```

**Or skip the intermediate index — filter logs by form type directly:**

```bash
edgar-research logs --year 2023 --forms 10-K N-CSR --out ./data/logs
```

**Summarise one filing with an LLM:**

```bash
edgar-research summarise ./data/filings/0000320193_0000320193-23-000106.txt --focus risk
```

---

## Form-type selection

Specify any combination of forms explicitly, or use a named preset:

| Preset                  | Expands to                                        |
| ----------------------- | ------------------------------------------------- |
| `corporate-annual`      | `10-K`, `20-F`, `40-F`                            |
| `corporate-quarterly`   | `10-Q`, `6-K`                                     |
| `corporate-current`     | `8-K`                                             |
| `mutual-fund`           | `N-CSR`, `N-CSRS`, `N-Q`, `N-PX`, `N-CEN`         |
| `proxy`                 | `DEF 14A`, `DEFA14A`, `PRE 14A`                   |
| `insider`               | `3`, `4`, `5`                                     |
| `ownership`             | `SC 13D`, `SC 13G`, `13F-HR`, `13F-NT`            |
| `registration`          | `S-1`, `S-3`, `S-4`, `F-1`, `F-3`                 |

Quote multi-word form types: `--forms "DEF 14A" "SC 13D"`.

Amendments (`/A`) are included by default. Use `--no-amendments` to
exclude them.

---

## Command reference

```text
edgar-research forms        --years Y[-Y]... (--forms FORM... | --preset GROUP)
                             --out DIR [--index CSV] [--no-amendments]
                             [--no-skip-existing]

edgar-research build-index  --years Y[-Y]... (--forms FORM... | --preset GROUP)
                             --out CSV [--no-amendments]

edgar-research logs         --year YYYY --out DIR
                             (--index CSV | --forms FORM... | --preset GROUP)
                             [--index-years Y[-Y]...] [--no-amendments]

edgar-research summarise    PATH [--focus TEXT] [--out FILE]
```

Run `edgar-research <cmd> --help` for per-command details.

---

## Using with AI agents (MCP)

Expose the full pipeline to Claude Code, Cursor, or any MCP-compatible
client:

```bash
claude mcp add edgar-research -- edgar-research-mcp
```

Tools available once registered:

- `list_form_presets()` — discover preset groups
- `download_edgar_filings(years, form_types, out_dir)`
- `build_accession_index(years, form_types, out_path)`
- `download_traffic_logs(year, index_csv, out_dir)`
- `summarise_edgar_filing(path, focus=None)`

The repo also ships a [Claude Skill](skills/edgar-research.md) so agents
discover the tool automatically when users ask about SEC filings or
retail-attention measurement.

---

## Repository layout

```
src/edgar_research/     Importable package
  client.py             Fair-access-policy HTTP (User-Agent, 8 rps, retry)
  forms.py              Filings downloader — any form type via form.idx
  logs.py               Daily traffic log downloader + retail filter
  index.py              Accession CSV read/write
  summarise.py          LLM summariser (Gemini / Claude)
  cli.py                argparse CLI
  mcp_server.py         MCP wrapper
skills/                 Claude Code skill definition
tests/                  pytest suite
legacy/                 Original Colab scripts from the paper (preserved for reproducibility)
```

---

## Differences vs the original paper scripts

The 2024 release (still in [`legacy/`](legacy/)) was Colab-only, N-CSR
only, and had a silent file-corruption bug. This rewrite:

- **Fixes** the bytes-vs-`str(bytes)` write bug that corrupted every
  downloaded filing in the original `Download EDGAR forms.py`.
- **Supports every form type** via SEC's `form.idx`, not only `N-CSR`.
- **Declares a User-Agent per SEC's EDGAR fair-access policy**
  (required since 2021) and rate-limits to 8 req/s (below SEC's 10-rps
  ceiling) with exponential backoff.
- **Removes hard-coded Colab paths** — everything is a CLI argument.
- **Resumes** mid-year: days that already succeeded are skipped.
- **Ships as a pip-installable package** with CLI, MCP server, and tests.

---

## Testing

```bash
pytest
ruff check src tests
```

CI runs on Python 3.10 / 3.11 / 3.12.

---

## Citation

If you use this code or reproduce the paper, please cite:

```bibtex
@article{Ding2024EDGARtraffic,
  title   = {Retail Investor Attention and Mutual Fund Performance: Evidence from EDGAR Log Files},
  author  = {Ding, Hao},
  year    = {2024},
  url     = {https://ssrn.com/abstract=4992233}
}
```

---

## License

[Apache 2.0](LICENSE). See `LICENSE` for the full text.

Contact: [haodingresearch@gmail.com](mailto:haodingresearch@gmail.com)
