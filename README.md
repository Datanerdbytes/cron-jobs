# cron-jobs — email-prune on GitHub Actions

Weekly GitHub Actions cron that runs `prune_email.py` to permanently delete
everything in Spam/Junk and Deleted Items/Trash for Gmail, Outlook.com and
iCloud. No local machine needed.

## How it works

- **Schedule**: Mondays 08:00 UTC — 09:00 CET in winter, 10:00 CEST in summer
  (edit the `cron` line in `.github/workflows/prune-email.yml` to change it;
  GitHub cron is always UTC).
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
   wait for Saturday.

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
