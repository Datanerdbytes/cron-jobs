# cron-jobs — email cleanup on GitHub Actions

Two GitHub Actions crons, no local machine needed:

- **`purge-senders.yml`** — daily at **00:00 Asia/Manila** (16:00 UTC): moves
  INBOX mail from the senders in `senders.example.json` (GitHub, CodeRabbit)
  to Trash. Recoverable until the weekly prune.
- **`prune-email.yml`** — Mondays 08:00 UTC (**16:00 Asia/Manila**): runs
  `prune_email.py` to permanently delete everything in Spam/Junk and
  Deleted Items/Trash for Gmail, Outlook.com and iCloud.

## How it works

- **Schedule**: purge daily at 16:00 UTC, prune Mondays 08:00 UTC. GitHub cron
  is always UTC, so 16:00 UTC is midnight in Manila; edit the `cron` lines in
  `.github/workflows/` to change the times.
- **Safety**: scheduled runs pass `--execute` (real deletion). Manual runs
  default to a dry-run; tick the **execute** checkbox in the
  "Run workflow" dialog to delete for real.
- **Credentials** live only in repo secrets — never in the code or config file.
- Providers whose secrets aren't configured are skipped automatically, so you
  can migrate one mailbox at a time.

## One-time setup

1. Create a private GitHub repo and push this folder:

   ```bash
   git init
   git add .
   git commit -m "email-prune cron via GitHub Actions"
   git remote add origin git@github.com:<you>/<repo>.git
   git push -u origin main
   ```

2. Add repo secrets (**Settings → Secrets and variables → Actions → New
   repository secret**) for each provider you want to prune:

   | Secret           | Value                                    |
   |------------------|------------------------------------------|
   | `EP_GMAIL_USER`  | `you@gmail.com`                          |
   | `EP_GMAIL_PASS`  | Gmail **app password** (needs 2FA on)    |
   | `EP_OUTLOOK_USER`| `you@outlook.com`                        |
   | `EP_OUTLOOK_PASS`| Outlook app password                     |
   | `EP_ICLOUD_USER` | `you@icloud.com`                         |
   | `EP_ICLOUD_PASS` | iCloud app password (appleid.apple.com)  |

   Only add the providers you actually use — the rest are skipped.

3. Verify Actions is enabled (**Settings → Actions → General** → allow all
   actions; on private repos, scheduled workflows are included).

4. Go to **Actions → email-prune → Run workflow**, leave "execute" unticked,
   and check the run output: it should show message counts (dry-run mode).

5. Once the dry-run looks right, run it again with **execute** ticked, or just
   wait for Monday.

## Reliability: external trigger

GitHub's cron scheduler is best-effort: scheduled runs can be delayed by
minutes-to-hours or silently dropped, and private repos have had prolonged
outages of `schedule` delivery. `workflow_dispatch` is not affected. To make
the daily sweep dependable, have an external scheduler call the API:

```bash
curl -X POST \
  -H "Authorization: Bearer $GH_PAT" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/Datanerdbytes/cron-jobs/actions/workflows/purge-senders.yml/dispatches \
  -d '{"ref":"main","inputs":{"execute":"true"}}'
```

Use a fine-grained token limited to this repo with **Actions: Read and write**.
Any scheduler that can send that header works (cron-job.org, Vercel cron,
Render cron). Keep the `schedule:` trigger as a fallback.

`inputs.execute` is required because manual dispatches default to a dry run.
For the weekly permanent delete, use the same call against
`prune-email.yml`.

## Notes

- Scheduled workflows can start 5–30 minutes late; harmless for a weekly prune.
- Private repos include 2,000 free Actions minutes/month; this job uses ~1 min
  per run (Python stdlib only, no dependencies to install).
- GitHub disables scheduled workflows after 60 days of repo inactivity — if
  that happens, re-enable from the Actions tab. A no-op commit occasionally
  keeps it alive.
- IMAP logins from GitHub's IPs may occasionally trip a provider's rate
  limiting; a weekly cadence makes that unlikely.

## Local run (unchanged)

```bash
export EP_GMAIL_USER="you@gmail.com"
export EP_GMAIL_PASS="abcd-efgh-ijkl-mnop"

python3 prune_email.py                 # dry-run
python3 prune_email.py --execute       # actually delete
```
