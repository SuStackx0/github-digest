import base64
import tempfile
from pathlib import Path
import pytest
from researcher import generate_analysis, generate_pdf, build_email_snippet

MOCK_REPO = {
    "owner": "openai",
    "name": "whisper",
    "description": "Robust Speech Recognition via Large-Scale Weak Supervision",
    "language": "Python",
    "total_stars": "48000",
    "forks": "3200",
    "stars_today": "1234",
    "url": "https://github.com/openai/whisper",
    "readme_text": (
        "# Whisper\n"
        "Whisper is an automatic speech recognition (ASR) system trained on 680,000 hours "
        "of multilingual and multitask supervised data collected from the web.\n"
        "## Architecture\n"
        "Encoder-decoder transformer. Audio is split into 30-second chunks.\n"
        "## How it works\n"
        "The model processes audio spectrogram inputs and generates text tokens.\n"
        "## Installation\n"
        "```bash\n"
        "pip install openai-whisper\n"
        "```\n"
        "## Limitations\n"
        "Performance degrades on low-resource languages.\n"
    ),
    "languages": {"Python": 95000, "Shell": 2000},
    "recent_commits": [
        {"sha": "abc123", "commit": {"message": "fix: improve long-form transcription accuracy"}}
    ],
    "api_data": {
        "stargazers_count": 48000,
        "forks_count": 3200,
        "open_issues_count": 42,
        "license": {"name": "MIT License"},
        "topics": ["speech-recognition", "deep-learning", "transformer"],
    },
}


def test_generate_analysis_returns_dict():
    a = generate_analysis(MOCK_REPO, rank=1)
    assert isinstance(a, dict)
    assert a["rank"] == 1
    assert a["title"] == "openai/whisper"
    assert a["url"] == "https://github.com/openai/whisper"


def test_generate_analysis_has_all_sections():
    a = generate_analysis(MOCK_REPO, rank=1)
    required = ["problem", "purpose", "architecture", "methodology", "components",
                "algorithms", "implementation", "tradeoffs", "use_cases",
                "limitations", "concepts", "takeaways"]
    for key in required:
        assert key in a["sections"], f"Missing section: {key}"
        assert isinstance(a["sections"][key], str)
        assert len(a["sections"][key]) > 10, f"Section too short: {key}"


def test_generate_analysis_extracts_limitations():
    a = generate_analysis(MOCK_REPO, rank=1)
    assert "low-resource" in a["sections"]["limitations"].lower() or len(a["sections"]["limitations"]) > 20


def test_generate_analysis_has_email_snippet():
    a = generate_analysis(MOCK_REPO, rank=1)
    assert isinstance(a["email_snippet"], str)
    assert len(a["email_snippet"]) > 20


def test_generate_analysis_handles_empty_readme():
    repo = {**MOCK_REPO, "readme_text": ""}
    a = generate_analysis(repo, rank=2)
    assert a["rank"] == 2
    for key in ["problem", "architecture", "takeaways"]:
        assert len(a["sections"][key]) > 5


def test_generate_pdf_creates_file():
    a = generate_analysis(MOCK_REPO, rank=1)
    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = Path(tmp) / "test_digest.pdf"
        generate_pdf([a], pdf_path)
        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 5000


def test_generate_pdf_multiple_repos():
    a1 = generate_analysis(MOCK_REPO, rank=1)
    a2 = generate_analysis({**MOCK_REPO, "owner": "microsoft", "name": "TypeChat",
                             "description": "Type-safe LLM structured outputs", "rank": 2}, rank=2)
    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = Path(tmp) / "multi.pdf"
        generate_pdf([a1, a2], pdf_path)
        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 8000


def test_build_email_snippet():
    a = generate_analysis(MOCK_REPO, rank=1)
    snippet = build_email_snippet(a)
    assert isinstance(snippet, str)
    assert len(snippet) > 10
