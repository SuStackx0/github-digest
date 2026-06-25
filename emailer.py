import base64
import logging
import os
from datetime import datetime
from pathlib import Path

import resend
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

RECIPIENT = "gs703880@gmail.com"
SENDER = "onboarding@resend.dev"
SEPARATOR = "━" * 40


def build_email_body(analyses: list, date_str: str = "") -> str:
    if not date_str:
        date_str = datetime.now().strftime("%A, %B %-d, %Y")

    lines = [
        "Good morning, Sumanth!",
        "",
        "Here are today's top 3 trending repos on GitHub.",
        "Full analysis PDF is attached.",
        "",
        SEPARATOR,
    ]

    for a in analyses:
        lines += [
            "",
            f"#{a['rank']} · {a['title']}",
            f"→ {a['url']}",
            a.get('email_snippet', a.get('description', '')),
            "",
            SEPARATOR,
        ]

    lines += [
        "",
        "Open the PDF for the complete deep-dive on each repo.",
        "",
        "— Your GitHub Digest",
    ]
    return "\n".join(lines)


def _build_failure_body(error: str, date_str: str) -> str:
    return (
        f"Today's GitHub Trending Digest could not be generated ({date_str}).\n"
        f"Error: {error}\n"
        "No digest was sent today. The system will retry tomorrow at 8am. "
        "Check /var/log/github_digest.log for the full error trace."
    )


def _encode_attachment(path: Path, mime_type: str = "application/pdf") -> dict:
    with open(path, "rb") as f:
        content = base64.b64encode(f.read()).decode()
    return {
        "filename": path.name,
        "content": content,
        "type": mime_type,
    }


def send_digest(
    repos: list,
    analyses: list,
    pdf_path=None,
    failed: bool = False,
    error: str = "",
) -> None:
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
        body = build_email_body(analyses, date_str=date_str)
        attachments = []
        if pdf_path and Path(pdf_path).exists():
            attachments.append(_encode_attachment(Path(pdf_path), "application/pdf"))
        params = {
            "from": SENDER,
            "to": [RECIPIENT],
            "subject": f"🔭 GitHub Trending Digest — {date_str}",
            "text": body,
            "attachments": attachments,
        }

    result = resend.Emails.send(params)
    log.info(f"Email sent: id={result.get('id')}")
