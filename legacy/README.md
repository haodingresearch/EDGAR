# Legacy scripts

The two files here are the original Colab-flavoured Python scripts that
shipped with the paper:

- `download_edgar_forms.py`
- `download_edgar_traffic_log.py`

They are preserved **verbatim** (only the filenames were de-spaced for
POSIX friendliness) so the paper's reproducibility claim still holds. The
hard-coded Google Drive paths, a `User-Agent` that doesn't meet SEC's
EDGAR fair-access policy, and the `str(bytes)` write bug are all
documented issues — use the new `edgar-research` CLI instead for any
fresh work.

```bibtex
@article{Ding2024EDGARtraffic,
  title={Retail Investor Attention and Mutual Fund Performance: Evidence from EDGAR Log Files},
  author={Ding, Hao},
  year={2024},
  url={https://ssrn.com/abstract=4992233}
}
```
