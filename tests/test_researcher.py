import pytest
from researcher import generate_report

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
        "# Whisper\n\nWhisper is an automatic speech recognition (ASR) system trained on "
        "680,000 hours of multilingual data.\n\n## Architecture\n\nEncoder-decoder transformer. "
        "Audio is split into 30-second chunks.\n\n## Usage\n\n```python\nimport whisper\n"
        "model = whisper.load_model('base')\nresult = model.transcribe('audio.mp3')\n```\n\n"
        "## Available Models\n\ntiny, base, small, medium, large\n"
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


def test_generate_report_returns_string():
    report = generate_report(MOCK_REPO, rank=1)
    assert isinstance(report, str)
    assert len(report) > 500


def test_generate_report_includes_header():
    report = generate_report(MOCK_REPO, rank=1)
    assert "whisper" in report.lower()
    assert "48000" in report or "48,000" in report


def test_generate_report_includes_all_sections():
    report = generate_report(MOCK_REPO, rank=1)
    required_sections = ["TL;DR", "What problem", "System Design", "Why it", "Quick reference"]
    for section in required_sections:
        assert section in report, f"Missing section: {section}"


def test_generate_report_includes_quick_reference_table():
    report = generate_report(MOCK_REPO, rank=1)
    assert "https://github.com/openai/whisper" in report
    assert "openai" in report


def test_generate_report_rank_2():
    report = generate_report(MOCK_REPO, rank=2)
    assert "#2" in report or "2" in report


def test_generate_report_handles_missing_readme():
    repo = {**MOCK_REPO, "readme_text": ""}
    report = generate_report(repo, rank=1)
    assert isinstance(report, str)
    assert len(report) > 200


def test_generate_report_formats_language_breakdown():
    report = generate_report(MOCK_REPO, rank=1)
    assert "Python" in report
