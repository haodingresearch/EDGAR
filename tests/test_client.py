"""Tests for the SEC fair-access HTTP client."""
from __future__ import annotations

import time

import pytest

from edgar_research.client import SEC_MAX_RPS, SECClient, UserAgentError, require_user_agent


def test_user_agent_required(monkeypatch):
    monkeypatch.delenv("EDGAR_USER_AGENT", raising=False)
    with pytest.raises(UserAgentError):
        require_user_agent()


def test_user_agent_rejects_missing_email(monkeypatch):
    monkeypatch.setenv("EDGAR_USER_AGENT", "Jane Researcher")
    with pytest.raises(UserAgentError):
        require_user_agent()


def test_user_agent_rejects_missing_name(monkeypatch):
    monkeypatch.setenv("EDGAR_USER_AGENT", "jane@example.com")
    with pytest.raises(UserAgentError):
        require_user_agent()


def test_user_agent_accepts_well_formed(monkeypatch):
    monkeypatch.setenv("EDGAR_USER_AGENT", "Jane Researcher jane@example.com")
    assert require_user_agent() == "Jane Researcher jane@example.com"


def test_client_rejects_excessive_rps(monkeypatch):
    monkeypatch.setenv("EDGAR_USER_AGENT", "Jane Researcher jane@example.com")
    with pytest.raises(ValueError):
        SECClient(rps=SEC_MAX_RPS + 1)


def test_client_throttle_enforces_interval(monkeypatch):
    monkeypatch.setenv("EDGAR_USER_AGENT", "Jane Researcher jane@example.com")
    client = SECClient(rps=4.0)
    start = time.monotonic()
    client._throttle()
    client._throttle()
    client._throttle()
    elapsed = time.monotonic() - start
    # 3 calls at 4 rps → at least 2 intervals of 0.25s between them
    assert elapsed >= 0.5 - 0.05  # small tolerance for timer skew
    client.close()
