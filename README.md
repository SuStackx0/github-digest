# GitHub Trending Digest

Scrapes the top 3 GitHub trending repos each morning, generates a deep markdown report per repo, and emails them to you daily at 8am.

## Prerequisites

- Python 3.8+
- A free [Resend](https://resend.com) account (takes 2 minutes, no credit card)

## Installation

```bash
git clone git@github-sustackx0:SuStackx0/github-digest.git ~/github-digest
cd ~/github-digest
bash setup.sh
```

setup.sh will prompt for your Resend API key, install dependencies, register the cron job, and send a test email immediately.

## Getting a Resend API key

1. Sign up at [resend.com](https://resend.com) — free tier, no domain verification needed
2. Go to API Keys → Create API Key
3. Copy the key (starts with re_) and paste it when setup.sh asks

## Manual run

```bash
~/github-digest/venv/bin/python ~/github-digest/daily_digest.py --test
```

## Logs

```bash
tail -f /var/log/github_digest.log
```

If /var/log/ is not writable, logs go to stdout only.

## Change email delivery time

```bash
crontab -e
# Edit the line starting with "0 8 * * *" — change "8" to your desired hour (24h format)
```

## Change recipient email

Edit emailer.py and update the RECIPIENT constant at the top of the file.

## Environment variables

| Variable | Required | Description |
|---|---|---|
| RESEND_API_KEY | Yes | Your Resend API key |
| GITHUB_TOKEN | No | GitHub personal access token (raises API rate limit from 60 to 5000 req/hr) |
