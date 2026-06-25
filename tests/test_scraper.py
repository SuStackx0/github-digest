import base64
import pytest
from unittest.mock import patch, MagicMock
from scraper import scrape_trending, _fetch_repo_api_data, _parse_trending_page

TRENDING_HTML = """
<article class="Box-row">
  <h2 class="h3 lh-condensed">
    <a href="/openai/whisper">openai / whisper</a>
  </h2>
  <p class="col-9 color-fg-muted my-1 pr-3">Robust Speech Recognition via Large-Scale Weak Supervision</p>
  <span class="d-inline-block mr-3" itemprop="programmingLanguage">Python</span>
  <a href="/openai/whisper/stargazers">48,000</a>
  <a href="/openai/whisper/forks">3,200</a>
  <span class="d-inline-block float-sm-right">
    <svg></svg> 1,234 stars today
  </span>
</article>
"""

MOCK_API_RESPONSE = {
    "full_name": "openai/whisper",
    "description": "Robust Speech Recognition",
    "stargazers_count": 48000,
    "forks_count": 3200,
    "language": "Python",
    "html_url": "https://github.com/openai/whisper",
    "owner": {"login": "openai"},
    "name": "whisper",
}

MOCK_README = {
    "content": base64.b64encode(b"# Whisper\nAutomatic speech recognition model.").decode()
}


def test_parse_trending_page_extracts_repos():
    repos = _parse_trending_page(TRENDING_HTML, limit=1)
    assert len(repos) == 1
    assert repos[0]["owner"] == "openai"
    assert repos[0]["name"] == "whisper"


def test_parse_trending_page_respects_limit():
    html = TRENDING_HTML * 5
    repos = _parse_trending_page(html, limit=3)
    assert len(repos) <= 3


def test_fetch_repo_api_data_decodes_readme():
    with patch("scraper.requests.get") as mock_get:
        responses = [
            MagicMock(status_code=200, json=lambda: MOCK_API_RESPONSE),
            MagicMock(status_code=200, json=lambda: MOCK_README),
            MagicMock(status_code=200, json=lambda: {"Python": 95000, "Shell": 2000}),
            MagicMock(status_code=200, json=lambda: [{"sha": "abc123", "commit": {"message": "fix bug"}}]),
        ]
        mock_get.side_effect = responses
        data = _fetch_repo_api_data("openai", "whisper")
    assert data["readme_text"].startswith("# Whisper")
    assert data["languages"] == {"Python": 95000, "Shell": 2000}


def test_fetch_repo_api_data_handles_missing_readme():
    with patch("scraper.requests.get") as mock_get:
        responses = [
            MagicMock(status_code=200, json=lambda: MOCK_API_RESPONSE),
            MagicMock(status_code=404, json=lambda: {}),
            MagicMock(status_code=200, json=lambda: {}),
            MagicMock(status_code=200, json=lambda: []),
        ]
        mock_get.side_effect = responses
        data = _fetch_repo_api_data("openai", "whisper")
    assert data["readme_text"] == ""


def test_scrape_trending_returns_enriched_repos():
    stub_repos = [{"owner": "openai", "name": "whisper", "description": "ASR", "language": "Python",
                   "stars_today": "1,234", "total_stars": "48,000", "forks": "3,200",
                   "url": "https://github.com/openai/whisper"}]
    api_stub = {"readme_text": "# Whisper", "languages": {"Python": 95000},
                "recent_commits": [], "api_data": MOCK_API_RESPONSE}
    with patch("scraper._parse_trending_page", return_value=stub_repos), \
            patch("scraper._fetch_repo_api_data", return_value=api_stub), \
            patch("scraper.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, text="<html></html>")
        repos = scrape_trending(limit=1)
    assert len(repos) == 1
    assert repos[0]["readme_text"] == "# Whisper"
