#!/bin/zsh
# Daily sender purge (GitHub/CodeRabbit -> Trash). Invoked by launchd.
# Credentials live in .env.local (gitignored, chmod 600).
set -eu
cd "$(dirname "$0")"
source ./.env.local
exec /opt/homebrew/bin/python3 purge_senders.py --execute --providers gmail
