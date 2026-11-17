#!/usr/bin/env python3
"""Weekly IMAP prune: permanently delete everything in Spam/Junk and Deleted Items/Trash.

Default mode is dry-run: it only counts what *would* be deleted. Pass --execute
to actually expunge the messages (irreversible).

Credentials are never stored in this repo. Set them as environment variables:

    export EP_GMAIL_USER="you@gmail.com"      # app password, not your account password
    export EP_GMAIL_PASS="abcd-efgh-ijkl-mnop"
    export EP_OUTLOOK_USER="you@outlook.com"
    export EP_OUTLOOK_PASS="..."
    export EP_ICLOUD_USER="you@icloud.com"
    export EP_ICLOUD_PASS="..."

Each provider entry maps folder names to the IMAP mailbox names the server uses.
Defaults below cover Gmail, Outlook.com/Office 365, and iCloud; override them in
--config if your folders are localized or non-standard.
"""

import argparse
import imaplib
import json
import os
import ssl
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

PROVIDER_DEFAULTS = {
    "gmail": {
        "host": "imap.gmail.com",
        "port": 993,
        "folders": {"spam": "[Gmail]/Spam", "deleted": "[Gmail]/Trash"},
    },
    "outlook": {
        "host": "outlook.office365.com",
        "port": 993,
        "folders": {"spam": "Junk Email", "deleted": "Deleted Items"},
    },
    "icloud": {
        "host": "imap.mail.me.com",
        "port": 993,
        "folders": {"spam": "Junk", "deleted": "Trash"},
    },
}


def load_config(path):
    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)

    providers = []
    for entry in raw.get("providers", []):
        name = entry["name"]
        defaults = PROVIDER_DEFAULTS.get(name, {})
        providers.append(
            {
                "name": name,
                "host": entry.get("host", defaults.get("host")),
                "port": int(entry.get("port", defaults.get("port", 993))),
                "user": os.environ[entry["user_env"]],
                "password": os.environ[entry["pass_env"]],
                "folders": {
                    "spam": entry.get("folders", {}).get(
                        "spam", defaults.get("folders", {}).get("spam", "Spam")
                    ),
                    "deleted": entry.get("folders", {}).get(
                        "deleted",
                        defaults.get("folders", {}).get("deleted", "Deleted Items"),
                    ),
                },
            }
        )
    return providers


def select(imap, folder):
    typ, _ = imap.select(folder, readonly=False)
    if typ != "OK":
        raise RuntimeError(f"cannot select mailbox {folder!r}: {typ}")


def count_messages(imap):
    typ, data = imap.uid("search", None, "ALL")
    if typ != "OK":
        raise RuntimeError(f"search failed: {typ}")
    return data[0].split() if data and data[0] else []


def prune_folder(imap, folder, execute):
    select(imap, folder)
    uids = count_messages(imap)
    total = len(uids)
    if total == 0:
        return 0, 0
    if not execute:
        return total, 0
    uid_list = ",".join(u.decode() if isinstance(u, bytes) else u for u in uids)
    typ, _ = imap.uid("store", uid_list, "+FLAGS", "(\\Deleted)")
    if typ != "OK":
        raise RuntimeError(f"mark deleted failed in {folder!r}: {typ}")
    typ, _ = imap.expunge()
    if typ != "OK":
        raise RuntimeError(f"expunge failed in {folder!r}: {typ}")
    remaining = len(count_messages(imap))
    return total, total - remaining


def run(providers, execute):
    summary = []
    ok = True
    ctx = ssl.create_default_context()
    for provider in providers:
        name = provider["name"]
        try:
            imap = imaplib.IMAP4_SSL(provider["host"], provider["port"], ssl_context=ctx)
            typ, _ = imap.login(provider["user"], provider["password"])
            if typ != "OK":
                raise RuntimeError(f"login failed: {typ}")
            for kind in ("spam", "deleted"):
                folder = provider["folders"][kind]
                try:
                    found, removed = prune_folder(imap, folder, execute)
                    summary.append(
                        {
                            "provider": name,
                            "folder": kind,
                            "mailbox": folder,
                            "messages": found,
                            "deleted": removed if execute else 0,
                        }
                    )
                except Exception as exc:  # one bad folder must not abort the rest
                    ok = False
                    summary.append(
                        {
                            "provider": name,
                            "folder": kind,
                            "mailbox": folder,
                            "messages": None,
                            "deleted": None,
                            "error": str(exc),
                        }
                    )
            try:
                imap.logout()
            except Exception:
                pass
        except Exception as exc:
            ok = False
            summary.append(
                {
                    "provider": name,
                    "folder": "connection",
                    "mailbox": "-",
                    "messages": None,
                    "deleted": None,
                    "error": str(exc),
                }
            )
    return summary, ok


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default=HERE / "providers.example.json",
        help="provider configuration JSON (default: scripts/email-prune/providers.example.json)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="actually delete messages (default is dry-run, counts only)",
    )
    parser.add_argument(
        "--providers",
        help="comma-separated subset of provider names to run, e.g. gmail,icloud",
    )
    args = parser.parse_args(argv)

    providers = load_config(args.config)
    if args.providers:
        wanted = {p.strip() for p in args.providers.split(",")}
        providers = [p for p in providers if p["name"] in wanted]

    summary, ok = run(providers, args.execute)

    mode = "EXECUTE" if args.execute else "dry-run"
    print(f"email-prune ({mode}):")
    for row in summary:
        if "error" in row:
            print(
                f"  {row['provider']}/{row['folder']} ({row['mailbox']}): ERROR {row['error']}"
            )
        else:
            verb = "deleted" if args.execute else "would delete"
            print(
                f"  {row['provider']}/{row['folder']} ({row['mailbox']}): "
                f"{row['messages']} messages, {verb} {row['deleted']}"
            )

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
