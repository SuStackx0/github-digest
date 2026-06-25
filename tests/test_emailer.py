import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import os
from emailer import build_email_body, send_digest

MOCK_REPOS = [
    {"owner": "openai", "name": "whisper", "description": "Speech Recognition",
     "language": "Python", "stars_today": "1234", "url": "https://github.com/openai/whisper"},
    {"owner": "microsoft", "name": "TypeChat", "description": "Type-safe LLM responses",
     "language": "TypeScript", "stars_today": "987", "url": "https://github.com/microsoft/TypeChat"},
    {"owner": "facebook", "name": "llama", "description": "Open LLM",
     "language": "Python", "stars_today": "756", "url": "https://github.com/facebook/llama"},
]


def test_build_email_body_contains_all_repos():
    body = build_email_body(MOCK_REPOS, date_str="Wednesday, June 25, 2026")
    assert "openai/whisper" in body
    assert "microsoft/TypeChat" in body
    assert "facebook/llama" in body


def test_build_email_body_contains_separator():
    body = build_email_body(MOCK_REPOS, date_str="Wednesday, June 25, 2026")
    assert "━" in body


def test_build_email_body_contains_stars():
    body = build_email_body(MOCK_REPOS, date_str="Wednesday, June 25, 2026")
    assert "1,234" in body or "1234" in body


def test_build_email_body_has_greeting():
    body = build_email_body(MOCK_REPOS, date_str="Wednesday, June 25, 2026")
    assert "Sumanth" in body


def test_send_digest_calls_resend():
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w") as f:
        f.write("# Test Report")
        tmp_path = f.name
    try:
        reports = [{"path": Path(tmp_path), "repo": MOCK_REPOS[0]}]
        with patch("emailer.resend.Emails.send") as mock_send:
            mock_send.return_value = {"id": "fake-id"}
            with patch.dict(os.environ, {"RESEND_API_KEY": "test-key"}):
                send_digest(repos=MOCK_REPOS, reports=reports)
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0][0]
        assert call_args["to"] == ["gs703880@gmail.com"]
        assert "GitHub Trending Digest" in call_args["subject"]
    finally:
        os.unlink(tmp_path)


def test_send_digest_failure_notification():
    with patch("emailer.resend.Emails.send") as mock_send:
        mock_send.return_value = {"id": "fake-id"}
        with patch.dict(os.environ, {"RESEND_API_KEY": "test-key"}):
            send_digest(repos=[], reports=[], failed=True, error="scraping timed out")
    call_args = mock_send.call_args[0][0]
    assert "Failed" in call_args["subject"] or "⚠️" in call_args["subject"]
    assert "scraping timed out" in call_args["text"]
