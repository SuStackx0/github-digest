#!/usr/bin/env python3
"""
Daily GitHub Trending Digest
Scrapes top 3 repos, generates skimmable markdown reports, emails them.
"""

import argparse
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_handlers = [logging.StreamHandler(sys.stdout)]
try:
    _handlers.append(logging.FileHandler("/var/log/github_digest.log", mode="a"))
except PermissionError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=_handlers,
)
log = logging.getLogger(__name__)

from scraper import scrape_trending
from researcher import generate_report
from emailer import send_digest


def run() -> None:
    log.info("Starting GitHub digest run")
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    try:
        repos = scrape_trending(limit=3)
        log.info(f"Scraped {len(repos)} repos")
    except Exception as e:
        log.error(f"Scraping failed: {e}")
        send_digest(repos=[], reports=[], failed=True, error=str(e))
        sys.exit(1)

    reports = []
    for i, repo in enumerate(repos, start=1):
        try:
            path = output_dir / f"repo_{i}_{repo['owner']}_{repo['name']}.md"
            content = generate_report(repo, rank=i)
            path.write_text(content, encoding="utf-8")
            reports.append({"path": path, "repo": repo})
            log.info(f"Report written: {path.name}")
        except Exception as e:
            log.error(f"Report generation failed for {repo['owner']}/{repo['name']}: {e}")

    if not reports:
        log.error("No reports generated — aborting")
        sys.exit(1)

    try:
        send_digest(repos=repos, reports=reports)
        log.info("Digest email sent successfully")
    except Exception as e:
        log.error(f"Email sending failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true",
                        help="Run immediately (same as cron run, just triggered manually)")
    parser.parse_args()
    run()
