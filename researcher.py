import logging
import re
from pathlib import Path

from fpdf import FPDF

log = logging.getLogger(__name__)

_README_MAX_CHARS = 10000
_SECTION_MAX_CHARS = 1200


def _format_number(n) -> str:
    try:
        return f"{int(str(n).replace(',', '')):,}"
    except (ValueError, TypeError):
        return str(n)


def _strip_markdown(text: str) -> str:
    text = re.sub(r'```.*?```', '[code omitted]', text, flags=re.DOTALL)
    text = re.sub(r'`[^`]+`', lambda m: m.group()[1:-1], text)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
    text = re.sub(r'_{1,3}([^_]+)_{1,3}', r'\1', text)
    text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'^[-*_]{3,}$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _sanitize(text: str) -> str:
    replacements = {
        '—': '--', '–': '-', ''': "'", ''': "'",
        '"': '"', '"': '"', '…': '...', '•': '-',
        '·': '-', '★': '*', '❤': '<3', ' ': ' ',
    }
    for char, rep in replacements.items():
        text = text.replace(char, rep)
    return text.encode('latin-1', errors='replace').decode('latin-1')


def _excerpt(readme: str) -> str:
    return readme[:_README_MAX_CHARS] if readme else ""


def _extract_section(readme: str, keywords: list, max_chars: int = _SECTION_MAX_CHARS) -> str:
    if not readme:
        return ""
    lines = readme.splitlines()
    result, in_section, section_level, chars = [], False, 0, 0
    for line in lines:
        m = re.match(r'^(#{1,6})\s+(.+)', line)
        if m:
            level = len(m.group(1))
            heading = m.group(2).lower()
            if in_section and level <= section_level:
                break
            if any(kw in heading for kw in keywords):
                in_section, section_level = True, level
                continue
        elif in_section:
            result.append(line)
            chars += len(line)
            if chars >= max_chars:
                break
    content = _strip_markdown("\n".join(result)).strip()
    return content[:max_chars] if content else ""


def _first_real_paragraph(readme: str, min_len: int = 60) -> str:
    if not readme:
        return ""
    for line in readme.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and not stripped.startswith('!') and len(stripped) >= min_len:
            return _strip_markdown(stripped)[:400]
    return ""


def _extract_code_example(readme: str) -> str:
    if not readme:
        return ""
    m = re.search(r'```[a-zA-Z]*\n(.*?)```', readme, re.DOTALL)
    if m:
        code = m.group(1).strip()
        lines = code.splitlines()[:10]
        return "\n".join(lines)
    return ""


def _language_breakdown(languages: dict) -> str:
    if not languages:
        return "Not specified"
    total = sum(languages.values()) or 1
    parts = [f"{lang} ({v/total*100:.0f}%)" for lang, v in sorted(languages.items(), key=lambda x: -x[1])[:4]]
    return ", ".join(parts)


def _infer_tradeoffs(repo: dict, readme: str) -> str:
    content = _extract_section(readme, ["tradeoff", "limitation", "caveat", "drawback", "consider", "decision"])
    if content:
        return content
    lang = repo.get('language', 'the chosen language')
    desc = repo.get('description', '')
    return (
        f"The project prioritises {desc.lower()[:80] if desc else 'its stated goal'} "
        f"over generality, a deliberate scope constraint common in focused open-source tools. "
        f"Choosing {lang} signals a trade-off favouring developer ergonomics or ecosystem access "
        f"over maximum runtime performance."
    )


def _infer_concepts(repo: dict, readme: str) -> str:
    topics = repo.get('api_data', {}).get('topics', [])
    lang = repo.get('language', '')
    desc = repo.get('description', '')
    base = f"Core concepts: {', '.join(topics[:6])}." if topics else f"Core domain: {desc[:100]}."
    base += f" Language used: {lang}."
    if readme:
        headings = [re.match(r'^#{1,6}\s+(.+)', l) for l in readme.splitlines()]
        headings = [m.group(1) for m in headings if m]
        if headings:
            base += f" Key sections in the README: {', '.join(headings[:6])}."
    return base


def _infer_takeaways(repo: dict, readme: str) -> str:
    lang = repo.get('language', 'the project language')
    stars_today = _format_number(repo.get('stars_today', '0'))
    desc = repo.get('description', '')
    code_example = _extract_code_example(readme)
    takeaway = (
        f"This repository demonstrates how to build {desc.lower()[:100] if desc else 'a focused tool'} "
        f"in {lang}. Its rapid growth ({stars_today} stars today) shows strong demand in this space. "
        f"Study how the project structures its public API and README for clarity — these patterns "
        f"transfer directly to your own projects."
    )
    if code_example:
        takeaway += f"\n\nThe minimal usage pattern illustrates the intended developer experience:\n{code_example[:300]}"
    return takeaway


def generate_analysis(repo: dict, rank: int) -> dict:
    owner = repo.get('owner', 'unknown')
    name = repo.get('name', 'unknown')
    description = repo.get('description', 'No description available')
    language = repo.get('language', 'Unknown')
    total_stars = _format_number(repo.get('total_stars', '0'))
    stars_today = _format_number(repo.get('stars_today', '0'))
    forks = _format_number(repo.get('forks', '0'))
    url = repo.get('url', f'https://github.com/{owner}/{name}')
    readme = _excerpt(repo.get('readme_text', ''))
    languages = repo.get('languages', {})
    api_data = repo.get('api_data', {})
    topics = api_data.get('topics', [])
    license_name = (api_data.get('license', {}) or {}).get('name', 'Not specified')
    open_issues = api_data.get('open_issues_count', 'N/A')
    commits = repo.get('recent_commits', [])
    recent_commit = commits[0]['commit']['message'].split('\n')[0] if commits else ''

    first_para = _first_real_paragraph(readme)
    lang_breakdown = _language_breakdown(languages)

    problem = (
        _extract_section(readme, ['problem', 'motivation', 'why', 'background', 'challenge', 'pain']) or
        f"{description}. This addresses a recurring pain point for developers working in this space."
    )

    purpose = (
        _extract_section(readme, ['purpose', 'goal', 'objective', 'about', 'introduction', 'what is']) or
        (first_para if first_para else description)
    )

    architecture = (
        _extract_section(readme, ['architecture', 'design', 'overview', 'how it works', 'system', 'structure']) or
        f"Built in {language} ({lang_breakdown}). "
        + (f"Key topics: {', '.join(topics[:5])}." if topics else "See README for architecture details.")
    )

    methodology = (
        _extract_section(readme, ['approach', 'method', 'algorithm', 'technique', 'strategy', 'pipeline', 'workflow']) or
        f"The project follows a {language}-based approach. "
        + (f"It focuses on {description.lower()[:120]}." if description else "")
    )

    components = (
        _extract_section(readme, ['component', 'module', 'part', 'structure', 'layout', 'folder', 'directory']) or
        f"The codebase is written in {language}. Language breakdown: {lang_breakdown}. "
        "Consult the repository structure for individual modules."
    )

    algorithms = (
        _extract_section(readme, ['algorithm', 'pattern', 'technique', 'model', 'method', 'implementation', 'core']) or
        f"The project implements {description.lower()[:120] if description else 'the described functionality'}. "
        + (f"Topics tagged: {', '.join(topics[:5])}." if topics else "")
    )

    implementation = (
        f"Language: {language}. Language breakdown: {lang_breakdown}.\n"
        f"Total stars: {total_stars}. Forks: {forks}. Open issues: {open_issues}. License: {license_name}.\n"
        + (f"Most recent commit: '{recent_commit}'." if recent_commit else "")
        + ("\n" + _extract_section(readme, ['install', 'usage', 'getting started', 'quick start', 'setup'], 800) or "")
    )

    tradeoffs = _infer_tradeoffs(repo, readme)

    use_cases = (
        _extract_section(readme, ['use case', 'example', 'usage', 'applications', 'who', 'demo', 'scenario']) or
        f"{description}. Applicable wherever developers need to {description.lower()[:100] if description else 'address this problem'}."
    )

    limitations = (
        _extract_section(readme, ['limitation', 'known issue', 'caveat', 'not supported', 'todo', 'roadmap']) or
        "No explicit limitations documented in the README. Check open issues on GitHub for known constraints."
    )

    concepts = _infer_concepts(repo, readme)
    takeaways = _infer_takeaways(repo, readme)

    first_line = first_para or description
    email_snippet = f"{first_line[:180].rstrip('.')}." if first_line else description
    if len(email_snippet) < 80 and description and description not in email_snippet:
        email_snippet = f"{description.rstrip('.')}. {email_snippet}"

    return {
        'rank': rank,
        'title': f"{owner}/{name}",
        'url': url,
        'description': description,
        'language': language,
        'total_stars': total_stars,
        'stars_today': stars_today,
        'forks': forks,
        'license': license_name,
        'open_issues': str(open_issues),
        'email_snippet': email_snippet[:220],
        'sections': {
            'problem': problem,
            'purpose': purpose,
            'architecture': architecture,
            'methodology': methodology,
            'components': components,
            'algorithms': algorithms,
            'implementation': implementation,
            'tradeoffs': tradeoffs,
            'use_cases': use_cases,
            'limitations': limitations,
            'concepts': concepts,
            'takeaways': takeaways,
        },
    }


def build_email_snippet(analysis: dict) -> str:
    return analysis.get('email_snippet', analysis.get('description', ''))


def generate_pdf(analyses: list, output_path) -> None:
    SECTION_LABELS = [
        ('problem',        '1. Problem Being Solved'),
        ('purpose',        '2. Purpose and Motivation'),
        ('architecture',   '3. High-Level Architecture and Design'),
        ('methodology',    '4. Core Methodology and Approach'),
        ('components',     '5. Important Components'),
        ('algorithms',     '6. Key Algorithms, Patterns, and Techniques'),
        ('implementation', '7. Important Implementation Details'),
        ('tradeoffs',      '8. Trade-offs and Design Decisions'),
        ('use_cases',      '9. Real-World Use Cases'),
        ('limitations',    '10. Limitations'),
        ('concepts',       '11. Key Concepts to Learn'),
        ('takeaways',      '12. Practical Takeaways'),
    ]

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(20, 20, 20)

    # Cover page
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 20)
    pdf.ln(30)
    pdf.cell(0, 12, _sanitize('GitHub Trending Digest'), ln=True, align='C')
    pdf.set_font('Helvetica', '', 12)
    if analyses:
        from datetime import datetime
        pdf.cell(0, 8, _sanitize(datetime.now().strftime('%A, %B %-d, %Y')), ln=True, align='C')
    pdf.ln(10)
    pdf.set_font('Helvetica', '', 11)
    pdf.cell(0, 7, _sanitize(f"Deep-dive analysis of {len(analyses)} trending repositories"), ln=True, align='C')
    pdf.ln(20)

    # TOC
    pdf.set_font('Helvetica', 'B', 13)
    pdf.cell(0, 9, 'Contents', ln=True)
    pdf.set_font('Helvetica', '', 11)
    pdf.ln(2)
    for a in analyses:
        pdf.cell(0, 7, _sanitize(f"  #{a['rank']}  {a['title']}  ({a['stars_today']} stars today)"), ln=True)
    pdf.ln(10)

    # Per-repo sections
    for a in analyses:
        pdf.add_page()

        # Repo header
        pdf.set_font('Helvetica', 'B', 16)
        pdf.cell(0, 10, _sanitize(f"#{a['rank']} -- {a['title']}"), ln=True)
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(0, 6, _sanitize(a['url']), ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)
        pdf.set_font('Helvetica', '', 11)
        meta_line = _sanitize(
            f"Stars today: {a['stars_today']}  |  Total: {a['total_stars']}  |  "
            f"Forks: {a['forks']}  |  Language: {a['language']}  |  License: {a['license']}"
        )
        pdf.multi_cell(0, 6, meta_line)
        pdf.ln(4)

        # Description
        pdf.set_font('Helvetica', 'I', 11)
        pdf.multi_cell(0, 6, _sanitize(a['description']))
        pdf.ln(6)

        # 12 sections
        for key, label in SECTION_LABELS:
            content = a['sections'].get(key, '').strip()
            if not content:
                continue

            # Section heading
            pdf.set_font('Helvetica', 'B', 12)
            pdf.cell(0, 8, _sanitize(label), ln=True)

            # Section body
            pdf.set_font('Helvetica', '', 11)
            pdf.multi_cell(0, 6, _sanitize(content))
            pdf.ln(5)

        pdf.ln(10)

    pdf.output(str(output_path))
