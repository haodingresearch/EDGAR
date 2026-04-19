---
name: edgar-research
description: Use when the user wants to download SEC EDGAR filings of any form type (10-K, 10-Q, 8-K, N-CSR, DEF 14A, 13F-HR, etc.), download and filter EDGAR daily traffic log files, build accession indexes, or LLM-summarise filings. Reproduces the methodology from Ding (2024), "Retail Investor Attention and Mutual Fund Performance" (SSRN 4992233), generalised beyond N-CSR.
---

# edgar-research

SEC-compliant toolkit for downloading EDGAR filings, filtering daily traffic logs, and summarising filings — any form type.

## Trigger this skill when

- User asks to download SEC filings of any form type (10-K, 10-Q, 8-K, N-CSR, N-CSRS, DEF 14A, 13F-HR, SC 13D, S-1, etc.)
- User wants to measure retail investor attention via EDGAR log files
- User references the paper "Retail Investor Attention and Mutual Fund Performance" / SSRN 4992233
- User wants an LLM summary of a specific filing
- User asks how to join filings with traffic data

## Prerequisites

1. **Set the SEC-required User-Agent** — SEC blocks requests without a declared contact:
   ```bash
   export EDGAR_USER_AGENT="Full Name your@email.com"
   ```
2. For `summarise`: set `GEMINI_API_KEY` (preferred, free tier) or `ANTHROPIC_API_KEY`.

## Install

```bash
pip install -e .            # core
pip install -e '.[ai]'      # adds LLM summariser
pip install -e '.[mcp,ai]'  # adds MCP server for agent use
```

## Common workflows

**Download filings of one or more form types:**
```bash
edgar-research forms --years 2023 --forms 10-K 10-Q --out ./data/filings
edgar-research forms --years 2020-2023 --preset mutual-fund --out ./data/filings --index ./data/index.csv
```

**Build an accession index without downloading filings:**
```bash
edgar-research build-index --years 2023 --forms N-CSR N-CSRS --out ./data/index.csv
```

**Filter daily logs to those accessions:**
```bash
edgar-research logs --year 2023 --index ./data/index.csv --out ./data/logs
# or shortcut (index is built implicitly):
edgar-research logs --year 2023 --forms 10-K N-CSR --out ./data/logs
```

**Summarise a single filing:**
```bash
edgar-research summarise ./data/filings/0000320193_0000320193-23-000106.txt --focus risk
```

## Preset form-type groups

- `corporate-annual` → 10-K, 20-F, 40-F
- `corporate-quarterly` → 10-Q, 6-K
- `corporate-current` → 8-K
- `mutual-fund` → N-CSR, N-CSRS, N-Q, N-PX, N-CEN (the paper's set)
- `proxy` → DEF 14A, DEFA14A, PRE 14A
- `insider` → 3, 4, 5
- `ownership` → SC 13D, SC 13G, 13F-HR, 13F-NT
- `registration` → S-1, S-3, S-4, F-1, F-3

## Agent integration

```bash
claude mcp add edgar-research -- edgar-research-mcp
```

Exposes `download_edgar_filings`, `build_accession_index`, `download_traffic_logs`, `summarise_edgar_filing`, and `list_form_presets` as MCP tools.

## Repo

https://github.com/haodingresearch/EDGAR

## Citation

```bibtex
@article{Ding2024EDGARtraffic,
  title={Retail Investor Attention and Mutual Fund Performance: Evidence from EDGAR Log Files},
  author={Ding, Hao},
  year={2024},
  url={https://ssrn.com/abstract=4992233}
}
```
