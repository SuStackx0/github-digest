import logging
import textwrap

log = logging.getLogger(__name__)

_README_MAX_CHARS = 8000


def _excerpt_readme(readme: str, max_chars: int = _README_MAX_CHARS) -> str:
    if not readme:
        return ""
    return readme[:max_chars] + ("..." if len(readme) > max_chars else "")


def _format_number(n) -> str:
    try:
        return f"{int(str(n).replace(',', '')):,}"
    except (ValueError, TypeError):
        return str(n)


def _language_breakdown(languages: dict) -> str:
    if not languages:
        return "Not specified"
    total = sum(languages.values()) or 1
    parts = [f"{lang} ({bytes_count / total * 100:.0f}%)" for lang, bytes_count in
             sorted(languages.items(), key=lambda x: -x[1])[:5]]
    return ", ".join(parts)


def _extract_usage_example(readme: str) -> str:
    if not readme:
        return ""
    in_block = False
    lines = []
    for line in readme.splitlines():
        if line.strip().startswith("```") and not in_block:
            in_block = True
            continue
        if line.strip().startswith("```") and in_block:
            break
        if in_block:
            lines.append(line)
    if lines:
        return "\n".join(lines[:12])
    return ""


def _derive_architecture(readme: str, repo: dict) -> str:
    if not readme:
        return "Architecture details not available — README not found."
    headings = [line.lstrip("#").strip() for line in readme.splitlines()
                if line.startswith("#") and len(line) > 3]
    arch_keywords = ["architecture", "design", "how it works", "overview", "system", "pipeline",
                     "model", "backend", "frontend", "components", "structure"]
    relevant = [h for h in headings if any(k in h.lower() for k in arch_keywords)]
    if relevant:
        return f"Key structural sections in the README: {', '.join(relevant[:5])}."
    return f"Built in {repo.get('language', 'multiple languages')} — see README for full architecture."


def _infer_tldr(repo: dict) -> str:
    name = repo.get("name", "unknown")
    owner = repo.get("owner", "")
    desc = repo.get("description", "").rstrip(".")
    stars_today = _format_number(repo.get("stars_today", "0"))
    language = repo.get("language", "")
    topics = repo.get("api_data", {}).get("topics", [])
    topic_str = f" It covers {', '.join(topics[:3])}." if topics else ""

    readme = repo.get("readme_text", "")
    first_para = ""
    if readme:
        for line in readme.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and len(stripped) > 40:
                first_para = stripped[:200]
                break

    tldr = f"**{owner}/{name}** — {desc}."
    if first_para:
        tldr += f" {first_para}"
    tldr += f"{topic_str} It gained {stars_today} stars today, signaling strong community interest."
    if language:
        tldr += f" Written in {language}."
    return tldr


def _infer_problem(repo: dict) -> str:
    desc = repo.get("description", "")
    readme = repo.get("readme_text", "")
    name = repo.get("name", "")

    if readme:
        for line in readme.splitlines():
            stripped = line.strip()
            if any(kw in stripped.lower() for kw in
                   ["problem", "motivation", "why", "pain", "challenge", "solves"]):
                return stripped[:400]

    return (f"{name.capitalize()} addresses the challenge of {desc.lower() or 'the problem described in the repo'}. "
            f"Engineers dealing with this space will find it directly applicable.")


def _infer_why_interesting(repo: dict) -> str:
    stars_today = _format_number(repo.get("stars_today", "0"))
    total_stars = _format_number(repo.get("total_stars", "0"))
    commits = repo.get("recent_commits", [])
    recent_msg = commits[0]["commit"]["message"].split("\n")[0] if commits else ""
    topics = repo.get("api_data", {}).get("topics", [])

    insight = (f"The repo pulled {stars_today} new stars in a single day against a base of "
               f"{total_stars} total — an unusually high velocity ratio.")
    if recent_msg:
        insight += f" The most recent commit ({recent_msg!r}) suggests active development."
    if topics:
        insight += f" Topics ({', '.join(topics[:4])}) place it squarely in a high-interest space right now."
    return insight


def generate_report(repo: dict, rank: int) -> str:
    owner = repo.get("owner", "unknown")
    name = repo.get("name", "unknown")
    description = repo.get("description", "No description provided")
    language = repo.get("language", "Unknown")
    total_stars = _format_number(repo.get("total_stars", "0"))
    forks = _format_number(repo.get("forks", "0"))
    stars_today = _format_number(repo.get("stars_today", "0"))
    url = repo.get("url", f"https://github.com/{owner}/{name}")
    readme = _excerpt_readme(repo.get("readme_text", ""))
    languages = repo.get("languages", {})
    api_data = repo.get("api_data", {})

    license_name = (api_data.get("license", {}).get("name", "Not specified")
                    if api_data.get("license") else "Not specified")
    open_issues = api_data.get("open_issues_count", "N/A")
    usage_example = _extract_usage_example(readme)
    arch_note = _derive_architecture(readme, repo)
    lang_breakdown = _language_breakdown(languages)

    usage_block = ""
    if usage_example:
        usage_block = f"""
### Usage example

```
{usage_example}
```
"""

    issues_note = ("active maintenance" if isinstance(open_issues, int) and open_issues > 0
                   else "early-stage or stable project")

    report = textwrap.dedent(f"""        # {name} — {description}

        ⭐ {total_stars} stars | 🍴 {forks} forks | {language} | 🔥 #{rank} trending today ({stars_today} new stars)

        ---

        ## TL;DR

        {_infer_tldr(repo)}

        ---

        ## What problem does it solve?

        {_infer_problem(repo)}

        ---

        ## How it works — System Design

        ### Architecture overview

        {arch_note}

        ### Key technical decisions

        - **Language choice:** {language} — {lang_breakdown}
        - **Scope:** {description}
        - **Open issues:** {open_issues} — indicates {issues_note}
        - **License:** {license_name}

        ### Tech stack

        - Language: {language}
        - Key frameworks / libraries: See README for full dependency list
        - Language breakdown: {lang_breakdown}
        {usage_block}
        ---

        ## Why it's interesting

        {_infer_why_interesting(repo)}

        ---

        ## Quick reference

        | Field | Value |
        |---|---|
        | Repo | {url} |
        | Stars today | {stars_today} |
        | Total stars | {total_stars} |
        | Language | {language} |
        | Owner | {owner} |
        | License | {license_name} |
        | Open issues | {open_issues} |
    """)

    return report
