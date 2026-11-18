#!/bin/zsh
# Weekly permanent prune of Spam + Trash. Invoked by launchd (Mondays 09:00).
# Credentials live in .env.local (gitignored, chmod 600).
set -eu
cd "$(dirname "$0")"
source ./.env.local
exec /opt/homebrew/bin/python3 prune_email.py --execute --providers gmail
