#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/venv"
LOG_FILE="/var/log/github_digest.log"
CRON_MARKER="github-digest"
CRON_CMD="0 8 * * * cd $SCRIPT_DIR && $VENV/bin/python daily_digest.py >> $LOG_FILE 2>&1"

echo "=== GitHub Trending Digest Setup ==="

PYTHON=$(command -v python3 || command -v python)
PY_MAJOR=$("$PYTHON" -c "import sys; print(sys.version_info.major)")
PY_MINOR=$("$PYTHON" -c "import sys; print(sys.version_info.minor)")
PY_VERSION=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 8 ]; }; then
    echo "ERROR: Python 3.8+ required. Found $PY_VERSION"
    exit 1
fi
echo "✓ Python $PY_VERSION"

if [ ! -d "$VENV" ]; then
    "$PYTHON" -m venv "$VENV"
    echo "✓ Virtualenv created"
else
    echo "✓ Virtualenv exists"
fi

"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q -r "$SCRIPT_DIR/requirements.txt"
echo "✓ Dependencies installed"

ENV_FILE="$SCRIPT_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo ""
    read -r -p "Enter your RESEND_API_KEY (required — get free at resend.com): " RESEND_API_KEY
    if [ -z "$RESEND_API_KEY" ]; then
        echo "ERROR: RESEND_API_KEY is required"
        exit 1
    fi
    read -r -p "Enter GITHUB_TOKEN (optional, press Enter to skip): " GITHUB_TOKEN

    {
        echo "RESEND_API_KEY=$RESEND_API_KEY"
        [ -n "$GITHUB_TOKEN" ] && echo "GITHUB_TOKEN=$GITHUB_TOKEN"
    } > "$ENV_FILE"
    echo "✓ .env written"
else
    echo "✓ .env exists"
fi

set -a; source "$ENV_FILE"; set +a
echo "✓ Env vars loaded"

if touch "$LOG_FILE" 2>/dev/null; then
    echo "✓ Log file ready: $LOG_FILE"
else
    echo "⚠ Cannot write to $LOG_FILE — logs will go to stdout only"
fi

if crontab -l 2>/dev/null | grep -qF "$CRON_MARKER"; then
    echo "✓ Cron job already registered"
else
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    echo "✓ Cron job registered (runs daily at 8am)"
fi

echo ""
echo "=== Running test digest ==="
"$VENV/bin/python" "$SCRIPT_DIR/daily_digest.py" --test

echo ""
echo "=== Setup complete ==="
echo "Daily digest will run at 8am. Check $LOG_FILE for logs."
echo "Manual run: $VENV/bin/python $SCRIPT_DIR/daily_digest.py --test"
