#!/usr/bin/env python3
"""
Daily GitHub Trending Digest
Scrapes top 3 repos, generates a PDF deep-dive report, emails it.
"""

import argparse
import logging
import sys
from datetime import datetime
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
from researcher import generate_analysis, generate_pdf
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
        send_digest(repos=[], analyses=[], failed=True, error=str(e))
        sys.exit(1)

    analyses = []
    for i, repo in enumerate(repos, start=1):
        try:
            analysis = generate_analysis(repo, rank=i)
            analyses.append(analysis)
            log.info(f"Analysis ready: {analysis['title']}")
        except Exception as e:
            log.error(f"Analysis failed for {repo.get('owner')}/{repo.get('name')}: {e}")

    if not analyses:
        log.error("No analyses generated — aborting")
        sys.exit(1)

    date_str = datetime.now().strftime("%Y-%m-%d")
    pdf_path = output_dir / f"github_digest_{date_str}.pdf"
    try:
        generate_pdf(analyses, pdf_path)
        log.info(f"PDF written: {pdf_path.name}")
    except Exception as e:
        log.error(f"PDF generation failed: {e}")
        sys.exit(1)

    try:
        send_digest(repos=repos, analyses=analyses, pdf_path=pdf_path)
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
