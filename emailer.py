import base64
import logging
import os
from datetime import datetime
from pathlib import Path

import resend
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

RECIPIENT = "gsumanthg2003@gmail.com"
SENDER = "onboarding@resend.dev"
SEPARATOR = "━" * 40


def build_email_body(repos: list, date_str: str = "") -> str:
    if not date_str:
        date_str = datetime.now().strftime("%A, %B %-d, %Y")

    lines = [
        "Good morning, Sumanth!",
        "",
        "Here are today's top 3 trending repos on GitHub.",
        "",
        SEPARATOR,
    ]

    for i, repo in enumerate(repos, start=1):
        owner = repo.get("owner", "")
        name = repo.get("name", "")
        desc = repo.get("description", "")
        stars_today = repo.get("stars_today", "0")
        try:
            stars_today = f"{int(str(stars_today).replace(',', '')):,}"
        except (ValueError, TypeError):
            pass
        language = repo.get("language", "")
        url = repo.get("url", "")

        lines += [
            "",
            f"#{i} · {owner}/{name}",
            desc,
            f"⭐ {stars_today} new stars today · {language}",
            f"→ {url}",
            "",
            SEPARATOR,
        ]

    lines += [
        "",
        "Full deep-dives are attached (3 markdown files).",
        "Open whichever repo catches your eye.",
        "",
        "— Your GitHub Digest",
    ]
    return "\n".join(lines)


def _build_failure_body(error: str, date_str: str) -> str:
    return (
        f"Today's GitHub Trending Digest could not be generated ({date_str}).\n"
        f"Error: {error}\n"
        "\n"
        "No digest was sent today. The system will retry tomorrow at 8am. "
        "Check /var/log/github_digest.log for the full error trace."
    )


def _encode_attachment(path: Path) -> dict:
    with open(path, "rb") as f:
        content = base64.b64encode(f.read()).decode()
    return {
        "filename": path.name,
        "content": content,
        "type": "text/markdown",
    }


def send_digest(repos: list, reports: list, failed: bool = False, error: str = "") -> None:
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        raise EnvironmentError("RESEND_API_KEY environment variable is not set")
    resend.api_key = api_key

    date_str = datetime.now().strftime("%A, %B %-d, %Y")

    if failed:
        params = {
            "from": SENDER,
            "to": [RECIPIENT],
            "subject": f"⚠️ GitHub Digest Failed — {date_str}",
            "text": _build_failure_body(error, date_str),
        }
    else:
        body = build_email_body(repos, date_str=date_str)
        attachments = [_encode_attachment(r["path"]) for r in reports if Path(r["path"]).exists()]
        params = {
            "from": SENDER,
            "to": [RECIPIENT],
            "subject": f"🔭 GitHub Trending Digest — {date_str}",
            "text": body,
            "attachments": attachments,
        }

    result = resend.Emails.send(params)
    log.info(f"Email sent: id={result.get('id')}")
