"""LLM-powered summarisation of a single EDGAR filing.

Gemini is tried first (free tier suits researchers), Claude is the fallback,
and the module fails loudly if neither ``GEMINI_API_KEY`` nor
``ANTHROPIC_API_KEY`` is available. Form-type detection from the filing header
lets us pass targeted guidance into the prompt — a 10-K summary should look
different from an N-CSR summary.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

FORM_GUIDANCE: dict[str, str] = {
    "10-K": "annual corporate report. Extract: business overview, material risk factors, MD&A highlights, financial trends.",
    "10-K/A": "amended annual report. Note what changed vs the original 10-K.",
    "10-Q": "quarterly report. Extract: period results, material changes vs prior quarter, outlook.",
    "8-K": "current report. Extract: what material event occurred, when, quantifiable impact.",
    "20-F": "foreign private issuer annual report. Extract: operations, regulatory exposure, financials.",
    "N-CSR": "mutual fund annual shareholder report. Extract: strategy, portfolio composition, performance vs benchmark, manager commentary.",
    "N-CSRS": "mutual fund semi-annual shareholder report. Same angles as N-CSR but six-month window.",
    "N-Q": "quarterly portfolio holdings schedule. Extract: top holdings, sector concentration, notable changes.",
    "N-PX": "proxy voting record. Extract: notable votes against management, ESG patterns.",
    "DEF 14A": "definitive proxy statement. Extract: voting matters, exec compensation, board composition.",
    "13F-HR": "institutional holdings report. Extract: top positions, concentration, notable new or exited positions.",
    "SC 13D": "beneficial-ownership filing (activist intent). Extract: stake size, stated purpose, investment thesis.",
    "SC 13G": "passive beneficial-ownership filing. Extract: stake size, filer, any historical pattern.",
    "S-1": "registration statement for an IPO or new offering. Extract: business, use of proceeds, risks, financials.",
}


_FORM_HEADER_RE = re.compile(
    r"(?:CONFORMED\s+SUBMISSION\s+TYPE|FORM\s+TYPE)\s*:\s*(\S.*?)\s*$",
    re.MULTILINE,
)


def _guess_form_type(text: str) -> str | None:
    m = _FORM_HEADER_RE.search(text[:10_000])
    return m.group(1).strip() if m else None


def _strip_html(raw: str) -> str:
    from bs4 import BeautifulSoup  # imported lazily — keeps import cost off cli startup

    soup = BeautifulSoup(raw, "lxml")
    return soup.get_text(separator="\n")


def _prepare_text(path: Path, max_chars: int = 120_000) -> tuple[str, str | None]:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    form_type = _guess_form_type(raw)
    body = _strip_html(raw) if "<html" in raw.lower() else raw
    body = re.sub(r"\n{3,}", "\n\n", body)
    body = re.sub(r"[ \t]+", " ", body)
    if len(body) > max_chars:
        half = max_chars // 2
        body = body[:half] + "\n\n[... content truncated for length ...]\n\n" + body[-half:]
    return body, form_type


def _build_prompt(text: str, form_type: str | None, focus: str | None) -> str:
    guidance = FORM_GUIDANCE.get(
        (form_type or "").upper(), "SEC filing. Extract the most decision-relevant facts."
    )
    focus_line = f"\nUser-specified focus: **{focus}**." if focus else ""
    return (
        "You are summarising an SEC EDGAR filing for a finance researcher.\n"
        f"Form type: {form_type or 'unknown'}\n"
        f"Form guidance: {guidance}{focus_line}\n\n"
        "Return a concise markdown summary (300-500 words) with these sections:\n"
        "- **Overview** (2-3 sentences)\n"
        "- **Key figures / facts** (bullet points, include numbers where available)\n"
        "- **Notable risks or changes** (bullet points)\n"
        "- **Bottom line** (1-2 sentences of takeaway)\n\n"
        "Filing content:\n---\n"
        f"{text}\n---"
    )


def _call_gemini(prompt: str, model: str = "gemini-2.0-flash") -> str:
    import google.generativeai as genai

    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set")
    genai.configure(api_key=key)
    resp = genai.GenerativeModel(model).generate_content(prompt)
    return (resp.text or "").strip()


def _call_claude(prompt: str, model: str = "claude-sonnet-4-6") -> str:
    import anthropic

    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    client = anthropic.Anthropic(api_key=key)
    msg = client.messages.create(
        model=model,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in msg.content if getattr(block, "text", None)).strip()


def summarise_filing(path: Path | str, focus: str | None = None) -> str:
    text, form_type = _prepare_text(Path(path))
    prompt = _build_prompt(text, form_type, focus)

    errors: list[str] = []
    if os.environ.get("GEMINI_API_KEY"):
        try:
            result = _call_gemini(prompt)
            if result:
                return result
            errors.append("Gemini: empty response")
        except Exception as e:
            errors.append(f"Gemini: {e}")

    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            result = _call_claude(prompt)
            if result:
                return result
            errors.append("Claude: empty response")
        except Exception as e:
            errors.append(f"Claude: {e}")

    if not errors:
        raise RuntimeError(
            "No LLM credentials found. Set GEMINI_API_KEY (preferred) or ANTHROPIC_API_KEY."
        )
    raise RuntimeError("All summarisation backends failed: " + " | ".join(errors))
