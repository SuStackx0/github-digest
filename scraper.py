import base64
import logging
import os
import time

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
TRENDING_URL = "https://github.com/trending"
RETRY_COUNT = 2
RETRY_DELAY = 5


def _headers() -> dict:
    h = {"Accept": "application/vnd.github.v3+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        h["Authorization"] = f"token {token}"
    return h


def _get_with_retry(url: str, **kwargs) -> requests.Response:
    for attempt in range(RETRY_COUNT + 1):
        try:
            resp = requests.get(url, timeout=15, **kwargs)
            if resp.status_code < 500:
                return resp
        except requests.RequestException as e:
            log.warning(f"Request error ({url}): {e}")
        if attempt < RETRY_COUNT:
            log.info(f"Retrying {url} in {RETRY_DELAY}s (attempt {attempt + 1})")
            time.sleep(RETRY_DELAY)
    log.error(f"Failed to fetch {url} after {RETRY_COUNT + 1} attempts")
    raise requests.RequestException(f"Max retries exceeded for {url}")


def _parse_trending_page(html: str, limit: int = 3) -> list:
    soup = BeautifulSoup(html, "html.parser")
    repos = []
    for article in soup.select("article.Box-row")[:limit]:
        link = article.select_one("h2 a, h1 a")
        if not link:
            continue
        parts = link["href"].strip("/").split("/")
        if len(parts) < 2:
            continue
        owner, name = parts[0], parts[1]

        desc_tag = article.select_one("p.col-9, p[itemprop='description']")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        lang_tag = article.select_one("[itemprop='programmingLanguage']")
        language = lang_tag.get_text(strip=True) if lang_tag else "Unknown"

        star_links = article.select("a[href*='stargazers'], a[href*='forks']")
        total_stars = star_links[0].get_text(strip=True).replace(",", "") if len(star_links) > 0 else "0"
        forks = star_links[1].get_text(strip=True).replace(",", "") if len(star_links) > 1 else "0"

        stars_today_tag = article.select_one("span.float-sm-right, span.d-inline-block.float-sm-right")
        stars_today_text = stars_today_tag.get_text(strip=True) if stars_today_tag else "0 stars today"
        stars_today = "".join(c for c in stars_today_text.split("stars")[0] if c.isdigit() or c == ",").strip()

        repos.append({
            "owner": owner,
            "name": name,
            "description": description,
            "language": language,
            "total_stars": total_stars,
            "forks": forks,
            "stars_today": stars_today or "0",
            "url": f"https://github.com/{owner}/{name}",
        })
    return repos


def _fetch_repo_api_data(owner: str, name: str) -> dict:
    result = {"readme_text": "", "languages": {}, "recent_commits": [], "api_data": {}}

    try:
        resp = _get_with_retry(f"{GITHUB_API}/repos/{owner}/{name}", headers=_headers())
        if resp.status_code == 200:
            result["api_data"] = resp.json()
    except Exception as e:
        log.warning(f"API metadata fetch failed for {owner}/{name}: {e}")

    try:
        resp = _get_with_retry(f"{GITHUB_API}/repos/{owner}/{name}/readme", headers=_headers())
        if resp.status_code == 200:
            encoded = resp.json().get("content", "")
            result["readme_text"] = base64.b64decode(encoded).decode("utf-8", errors="replace")
    except Exception as e:
        log.warning(f"README fetch failed for {owner}/{name}: {e}")

    try:
        resp = _get_with_retry(f"{GITHUB_API}/repos/{owner}/{name}/languages", headers=_headers())
        if resp.status_code == 200:
            result["languages"] = resp.json()
    except Exception as e:
        log.warning(f"Languages fetch failed for {owner}/{name}: {e}")

    try:
        resp = _get_with_retry(
            f"{GITHUB_API}/repos/{owner}/{name}/commits",
            headers=_headers(),
            params={"per_page": 5},
        )
        if resp.status_code == 200:
            result["recent_commits"] = resp.json()
    except Exception as e:
        log.warning(f"Commits fetch failed for {owner}/{name}: {e}")

    return result


def scrape_trending(limit: int = 3) -> list:
    resp = _get_with_retry(TRENDING_URL)
    repos = _parse_trending_page(resp.text, limit=limit)
    enriched = []
    for repo in repos:
        api_data = _fetch_repo_api_data(repo["owner"], repo["name"])
        enriched.append({**repo, **api_data})
    return enriched
