# cron-jobs — local (launchd) email cleanup

Two launchd agents run the email automation on this Mac. GitHub Actions
workflows are kept in the repo but **disabled** — its `schedule` trigger never
fired for these workflows (verified 28h+ with a `*/5` test cron), so the live
automation is local. Don't put this folder in `~/Documents`: macOS TCC blocks
launchd from reading protected folders (hence `~/cron-jobs`).

| Agent | When (Asia/Manila) | What |
|---|---|---|
| `com.cronjobs.purge-senders` | Daily **00:00** | Moves INBOX mail from `senders.example.json` (GitHub, CodeRabbit) to Trash |
| `com.cronjobs.email-prune` | **Mondays 09:00** | Permanently deletes everything in Spam and Trash |

Pipeline: the daily purge keeps the inbox clean (recoverable in Trash for up to
a week), the Monday prune empties Trash + Spam for good.

## Files

- `purge_senders.py` / `prune_email.py` — the scripts (`--execute` deletes;
  without it they only count)
- `senders.example.json` — senders to sweep (edit to add domains)
- `providers.example.json` — mailbox definitions; env var names for credentials
- `.env.local` — **local credentials, gitignored, `chmod 600`**. Also defines
  unused provider vars as empty strings so config loading passes
- `run-purge-senders.sh` / `run-email-prune.sh` — wrappers invoked by launchd
  (source `.env.local`, run with `--execute --providers gmail`)
- `~/Library/LaunchAgents/com.cronjobs.*.plist` — the agents
  (logs: `~/Library/Logs/cronjobs-*.log`)

## Common operations

```bash
# run now, exactly as launchd does
launchctl kickstart gui/$(id -u)/com.cronjobs.purge-senders
launchctl kickstart gui/$(id -u)/com.cronjobs.email-prune

# stop / start an agent
launchctl unload ~/Library/LaunchAgents/com.cronjobs.purge-senders.plist
launchctl load   ~/Library/LaunchAgents/com.cronjobs.purge-senders.plist

# check status (a "-" in the PID column means loaded and idle)
launchctl list | grep cronjobs
tail -5 ~/Library/Logs/cronjobs-purge-senders.log
```

launchd catches up on missed runs: if the Mac is asleep at 00:00, the sweep
runs when it next wakes.

## Changing the schedule

Edit `StartCalendarInterval` in the plist (local time, no UTC math needed),
then unload/load the agent. `Weekday` is 1 = Monday; omit it for daily.

## GitHub Actions (disabled, kept for reference)

`.github/workflows/` holds equivalent workflows (`workflow_dispatch` works
fine — `schedule` does not). Re-enable with:

```bash
gh workflow enable purge-senders.yml --repo Datanerdbytes/cron-jobs
gh workflow enable prune-email.yml  --repo Datanerdbytes/cron-jobs
```

Repo secrets (`EP_GMAIL_USER`, `EP_GMAIL_PASS`, …) remain configured there.
Manual dispatch defaults to a dry run; pass `-f execute=true` for real
deletion. An external scheduler (cron-job.org etc.) can also dispatch via the
API — see the workflow headers.

## Adding another mailbox

1. Add its `EP_*_USER` / `EP_*_PASS` exports to `.env.local`
2. Append the provider name to the wrappers' `--providers` list (e.g.
   `--providers gmail,icloud`)
3. Add matching repo secrets if you also use the GitHub path
