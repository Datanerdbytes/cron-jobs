#!/usr/bin/env python3
"""Daily sender purge: move every INBOX message from configured senders
(e.g. github.com, coderabbit.ai) to the provider's trash mailbox.

The point is a clean inbox every morning: notifications are swept out
nightly, and the weekly email-prune permanently deletes trash afterwards.

Default mode is dry-run: it only counts what *would* be moved. Pass --execute
to actually move messages to trash (recoverable until trash is emptied).

Credentials come from the same environment variables and provider config as
prune_email.py; the sender list lives in senders.example.json (override with
--senders).
"""

import argparse
import imaplib
import json
import ssl
import sys
from pathlib import Path

from prune_email import PROVIDER_DEFAULTS, load_config

HERE = Path(__file__).resolve().parent


def load_senders(path):
    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    senders = [s.strip() for s in raw.get("senders", []) if s.strip()]
    if not senders:
        raise SystemExit(f"no senders listed in {path}")
    return senders


def build_query(senders):
    """IMAP OR chain: OR FROM "a" FROM "b" -> OR OR FROM "a" FROM "b" FROM "c"."""
    parts = [f'FROM "{s}"' for s in senders]
    query = parts[0]
    for part in parts[1:]:
        query = f"OR {query} {part}"
    return query


def purge_inbox(imap, query, trash_mailbox, execute):
    typ, _ = imap.select("INBOX", readonly=False)
    if typ != "OK":
        raise RuntimeError("cannot select INBOX")
    typ, data = imap.uid("search", None, query)
    if typ != "OK":
        raise RuntimeError(f"search failed: {typ}")
    uids = data[0].split() if data and data[0] else []
    found = len(uids)
    if found == 0 or not execute:
        return found, 0

    uid_list = b",".join(uids)
    # Gmail IMAP cannot truly delete from INBOX: marking \\Deleted + expunge
    # only archives. Copying to Trash first means the message lands in the
    # trash mailbox; other providers just get an extra copy in Deleted Items
    # that the weekly prune removes.
    if trash_mailbox:
        typ, _ = imap.uid("COPY", uid_list, trash_mailbox)
        if typ != "OK":
            raise RuntimeError(f"copy to {trash_mailbox!r} failed: {typ}")
    typ, _ = imap.uid("store", uid_list, "+FLAGS", "(\\Deleted)")
    if typ != "OK":
        raise RuntimeError(f"mark deleted failed: {typ}")
    typ, _ = imap.expunge()
    if typ != "OK":
        raise RuntimeError(f"expunge failed: {typ}")
    return found, found


def run(providers, senders, execute):
    query = build_query(senders)
    summary = []
    ok = True
    ctx = ssl.create_default_context()
    for provider in providers:
        name = provider["name"]
        trash = provider["folders"]["deleted"]
        try:
            imap = imaplib.IMAP4_SSL(provider["host"], provider["port"], ssl_context=ctx)
            typ, _ = imap.login(provider["user"], provider["password"])
            if typ != "OK":
                raise RuntimeError(f"login failed: {typ}")
            try:
                found, moved = purge_inbox(imap, query, trash, execute)
                summary.append(
                    {
                        "provider": name,
                        "inbox": provider["user"],
                        "messages": found,
                        "moved": moved if execute else 0,
                    }
                )
            finally:
                try:
                    imap.logout()
                except Exception:
                    pass
        except Exception as exc:
            ok = False
            summary.append(
                {
                    "provider": name,
                    "inbox": provider["user"],
                    "messages": None,
                    "moved": None,
                    "error": str(exc),
                }
            )
    return query, summary, ok


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default=HERE / "providers.example.json",
        help="provider configuration JSON (same file as prune_email.py)",
    )
    parser.add_argument(
        "--senders",
        default=HERE / "senders.example.json",
        help="JSON list of senders to purge (default: senders.example.json)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="move matching messages to trash (default is dry-run, counts only)",
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

    senders = load_senders(args.senders)
    query, summary, ok = run(providers, senders, args.execute)

    mode = "EXECUTE" if args.execute else "dry-run"
    print(f"sender-purge ({mode}) — search: {query}")
    for row in summary:
        if "error" in row:
            print(f"  {row['provider']} ({row['inbox']}): ERROR {row['error']}")
        else:
            verb = "moved to trash" if args.execute else "would move to trash"
            print(f"  {row['provider']} ({row['inbox']}): {row['messages']} messages, {verb} {row['moved']}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
